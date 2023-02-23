package edu.lu.uni.serval.bug.fixer;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Calendar;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import anonymous.JsonInfo;
import anonymous.MethodLineFinder;
import anonymous.TestValidator;
import edu.lu.uni.serval.config.Configuration;
import edu.lu.uni.serval.fixminer.ProjectLiteral;
import edu.lu.uni.serval.fixminer.insertTemplate.InsertIfNonNullCheck;
import edu.lu.uni.serval.fixminer.insertTemplate.InsertIfNullCheck;
import edu.lu.uni.serval.fixminer.insertTemplate.InsertIfSizeCheck;
import edu.lu.uni.serval.fixminer.insertTemplate.StatementInserter;
import edu.lu.uni.serval.fixminer.insertTemplate.StatementMover;
import edu.lu.uni.serval.patch.Patch;
import edu.lu.uni.serval.templates.FixTemplate;
import edu.lu.uni.serval.utils.Checker;
import edu.lu.uni.serval.utils.FileHelper;
import edu.lu.uni.serval.utils.PathUtils;
import edu.lu.uni.serval.utils.SuspiciousPosition;
import edu.uni.lu.serval.fixminer.fixtemplate.DeleteStatement;
import edu.uni.lu.serval.fixminer.fixtemplate.IfNullChecker;
import edu.uni.lu.serval.fixminer.fixtemplate.IfOperator;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyBooleanArg;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyBooleanValue;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyExpStmtAssignMethodName;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyExpStmtMethodName;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyIfStmtMethodName;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyIfVariable;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyMethodInvocation;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyMethodInvocation.ModifyType;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyMethodQualifiedArgument;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyMethodVarArgument;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyModifier;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyNumberValue;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyPrimitiveType;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyReturnStmtMethodName;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyReturnStmtMethodVarRef;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyStringValue;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyVarDecStmtMethodName;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyVarDecStmtMethodVarArgument;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyVarDecStmtMethodVarArgument2MethodInvocation;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyVarDecStmtMethodVarRef;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyVariable;

/**
 * Automated Program Repair Tool: FixMiner.
 * 
 * @author kui.liu
 *
 */
public class FixMinerFixer extends AbstractFixer {
	
	private static Logger log = LoggerFactory.getLogger(FixMinerFixer.class);
	
	public List<ProjectLiteral> literals;
	
	public FixMinerFixer(String path, String projectName, int bugId, String defects4jPath) {
		super(path, projectName, bugId, defects4jPath);
	}
	
	public FixMinerFixer(String path, String metric, String projectName, int bugId, String defects4jPath) {
		super(path, metric, projectName, bugId, defects4jPath);
	}

	@Override
	public void fixProcess(int maxLocation) {
		// Read paths of the buggy project.
		if (!dp.validPaths) return;
		
		// Read suspicious positions.
		List<SuspiciousPosition> suspiciousCodeList = readSuspiciousCodeFromFile(metric, path, buggyProject, dp);
		if (suspiciousCodeList == null) return;
		
		log.info("=======Fixing Beginning======");
		long startTime=Calendar.getInstance().getTimeInMillis();
		List<SuspCodeNode> scns = new ArrayList<>();
		for (SuspiciousPosition suspiciousCode : suspiciousCodeList) {
			SuspCodeNode scn = parseSuspiciousCode(suspiciousCode);
			if (scn == null) continue;
			if (!methodLists.keySet().contains(scn.suspiciousJavaFile)){
				log.debug("Traverse AST for get all method lists: "+scn.suspiciousJavaFile);
				MethodLineFinder lineFinder=new MethodLineFinder(fullBuggyProjectPath+PathUtils.getSrcPath(buggyProject).get(2)+scn.suspiciousJavaFile);
				methodLists.put(PathUtils.getSrcPath(buggyProject).get(2).substring(1)+scn.suspiciousJavaFile, lineFinder.getFunctionLocations());
			}
			
//			System.err.println(scn.suspCodeStr);
	        // Match fix templates for this suspicious code with its context information.
	        fixWithMatchedFixTemplates(scn);
	        scns.add(scn);
			// if (minErrorTest == 0) break;

			if (maxLocation!=0 && suspiciousCode.rank>=maxLocation) {
				log.info("Max location reached!");
				break;
			}
        }
		jsonInfo.setSwitchInfos(switchInfos);
		jsonInfo.setMethodInfo(methodLists);
		jsonInfo.saveToFile(buggyProject,false);
		
		if (useSubTemplate) {
			// Reset Json Info for second group
			switchInfos.clear();
			jsonInfo=new JsonInfo(buggyProject);
			actualFailedTests=failedTestCasesStrList;
			actualPassedTests=new ArrayList<>(Arrays.asList(dp.testCases));
			failedPassingTests=new ArrayList<>();
			TestValidator testValid=new TestValidator(path,buggyProject,defects4jPath);
			try {
				List<String> failedPassTests=testValid.getFailedPassTests();
				for(String failedTest:failedPassTests){
					if (actualFailedTests.contains(failedTest)) {
						int index=actualFailedTests.indexOf(failedTest);
						actualFailedTests.remove(index);
						log.info("Remove "+failedTest+" from fail test");
					}

					failedPassingTests.add(failedTest);
				}
			} catch (IOException e) {
				log.error("Error on get failed tests:");
				e.printStackTrace();
			}
			jsonInfo.setTestList(actualFailedTests, actualPassedTests);
			jsonInfo.setFailedPassTest(failedPassingTests);
			for (JsonInfo.Location loc:flList){
				jsonInfo.addFaultLocation(loc);
			}

			subFixTemplates(scns,maxLocation);

			jsonInfo.setSwitchInfos(switchInfos);
			jsonInfo.setMethodInfo(methodLists);
			jsonInfo.saveToFile(buggyProject,true);	
			cacheInfo.saveCache(cachePath);
		}
		log.info("=======Finish off Fixing======");
		log.info("Running time: "+Long.toString((Calendar.getInstance().getTimeInMillis()-startTime)/1000));
		
		FileHelper.deleteDirectory(Configuration.TEMP_FILES_PATH + this.dataType + "/" + this.buggyProject);
	}

	private void fixWithMatchedFixTemplates(SuspCodeNode scn) {
		
		int suspiciousCodeType = scn.suspCodeAstNode.getType();
		
		// generate patches with fix templates.
		FixTemplate ft = null;
		if (Checker.isVariableDeclarationStatement(suspiciousCodeType)) {
			ft = new ModifyPrimitiveType();
			generatePatches(ft, scn);
			if (minErrorTest == 0) return;
			
			ft = new ModifyVarDecStmtMethodName();
			generatePatches(ft, scn);
			if (minErrorTest == 0) return;
			
			ft = new ModifyVarDecStmtMethodVarArgument();
			generatePatches(ft, scn);
			if (minErrorTest == 0) return;
			
			ft = new ModifyVarDecStmtMethodVarArgument2MethodInvocation();
			generatePatches(ft, scn);
			if (minErrorTest == 0) return;
			
			ft = new ModifyVarDecStmtMethodVarRef();
		} else if (Checker.isFieldDeclaration(suspiciousCodeType)) {
			ft = new ModifyModifier();
		} else if (Checker.isReturnStatement(suspiciousCodeType)) {
			ft = new ModifyMethodVarArgument();
			generatePatches(ft, scn);
			if (minErrorTest == 0) return;
			
			ft = new ModifyReturnStmtMethodName();
			generatePatches(ft, scn);
			if (minErrorTest == 0) return;
			
			ft = new ModifyReturnStmtMethodVarRef();
			generatePatches(ft, scn);
			if (minErrorTest == 0) return;
			
			ft = new ModifyBooleanArg();
			generatePatches(ft, scn);
			if (minErrorTest == 0) return;
			
			ft = new IfNullChecker();
		} else if (Checker.isExpressionStatement(suspiciousCodeType)) {
			ft = new ModifyBooleanArg();
			generatePatches(ft, scn);
			if (minErrorTest == 0) return;
			
			ft = new ModifyMethodVarArgument();
			generatePatches(ft, scn);
			if (minErrorTest == 0) return;
			
			ft = new ModifyMethodQualifiedArgument();
			generatePatches(ft, scn);
			if (minErrorTest == 0) return;
			
			ft = new ModifyExpStmtMethodName();
			generatePatches(ft, scn);
			if (minErrorTest == 0) return;
			
			ft = new ModifyExpStmtAssignMethodName();
		} else if (Checker.isIfStatement(suspiciousCodeType)) {
			ft = new IfOperator();
			generatePatches(ft, scn);
			if (minErrorTest == 0) return;
			
			ft = new ModifyIfStmtMethodName();
			generatePatches(ft, scn);
			if (minErrorTest == 0) return;
			
			ft = new ModifyMethodVarArgument();
			generatePatches(ft, scn);
			if (minErrorTest == 0) return;
			
			ft = new ModifyIfVariable();
			generatePatches(ft, scn);
			if (minErrorTest == 0) return;
			
			ft = new IfNullChecker();
		} else {
		}
		if (ft != null) {
			generatePatches(ft, scn);
		}
		if (minErrorTest == 0) return;
		ft = new InsertIfNonNullCheck();
		generatePatches(ft, scn);
		
		if (minErrorTest == 0) return;
		ft = new InsertIfNullCheck();
		generatePatches(ft, scn);
		
		if (minErrorTest == 0) return;
		ft = new InsertIfSizeCheck();
		generatePatches(ft, scn);
		
		if (minErrorTest == 0) return;
		ft = new StatementInserter();
		generatePatches(ft, scn);
		
		if (minErrorTest == 0) return;
		ft = new StatementMover();
		generatePatches(ft, scn);
		
		if (minErrorTest == 0) return;
		ft = new DeleteStatement();
		generatePatches(ft, scn);
		ft = null;
	}
	
	private void generatePatches(FixTemplate ft, SuspCodeNode scn) {
		ft.setSuspiciousCodeStr(scn.suspCodeStr);
		ft.setSuspiciousCodeTree(scn.suspCodeAstNode);
		ft.setLiterals(this.literals);
		if (scn.javaBackup == null) ft.setSourceCodePath(dp.srcPath);
		else ft.setSourceCodePath(dp.srcPath, scn.javaBackup);
		ft.generatePatches();
		List<Patch> patchCandidates = ft.getPatches();
		
		// Test generated patches.
		if (patchCandidates.isEmpty()) return;
		addPatchesToInfo(patchCandidates, scn);
		// testGeneratedPatches(patchCandidates, scn);
	}

	private void subFixTemplates(List<SuspCodeNode> scns,int maxLocation) {
		this.isSecondLoop=true;
		for (SuspCodeNode scn : scns) {
			FixTemplate ft = null;
			ft = new ModifyMethodInvocation(scn.suspCodeAstNode, ModifyType.DEFAULT);
			generatePatches(ft, scn);
			if (minErrorTest == 0) break;
			
			if (Checker.isTypeDeclaration(scn.suspCodeAstNode.getType())) {
				ft = new ModifyModifier();
				generatePatches(ft, scn);
				if (minErrorTest == 0) break;
			} else if (Checker.isMethodDeclaration(scn.suspCodeAstNode.getType())) {
				ft = new ModifyModifier();
				generatePatches(ft, scn);
				if (minErrorTest == 0) break;
			}
			
			ft = new ModifyVariable(true);
			generatePatches(ft, scn);
			if (minErrorTest == 0) break;
			
			ft = new ModifyBooleanValue();
			generatePatches(ft, scn);
			if (minErrorTest == 0) break;
			
			
			ft = new ModifyNumberValue();
			generatePatches(ft, scn);
			if (minErrorTest == 0) break;
			
			ft = new ModifyStringValue();
			generatePatches(ft, scn);
			if (minErrorTest == 0) break;
			
//			ft = new ModifyMethodInvocation(scn.suspCodeAstNode, ModifyType.DEFAULT);
//			generatePatches(ft, scn);
//			if (minErrorTest == 0) break;
			
			ft = null;

			if (maxLocation!=0 && scn.rank>=maxLocation) {
				log.info("Max location reached!");
				break;
			}
		}
	}

}
