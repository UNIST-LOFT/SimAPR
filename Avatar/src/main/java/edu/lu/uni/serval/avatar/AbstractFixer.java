package edu.lu.uni.serval.avatar;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;

import org.apache.commons.lang3.math.NumberUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import edu.lu.uni.serval.config.Configuration;
import edu.lu.uni.serval.dataprepare.DataPreparer;
import edu.lu.uni.serval.faultlocalization.FL;
import edu.lu.uni.serval.faultlocalization.SuspiciousCode;
import edu.lu.uni.serval.jdt.tree.ITree;
import edu.lu.uni.serval.utils.FileHelper;
import edu.lu.uni.serval.utils.FileUtils;
import edu.lu.uni.serval.utils.MethodLineFinder;
import edu.lu.uni.serval.utils.PathUtils;
import edu.lu.uni.serval.utils.ShellUtils;
import edu.lu.uni.serval.utils.SuspiciousCodeParser;
import edu.lu.uni.serval.utils.SuspiciousPosition;
import edu.lu.uni.serval.utils.TestUtils;
import kr.ac.unist.apr.CacheInfo;
import kr.ac.unist.apr.JsonInfo;
import kr.ac.unist.apr.MethodFinder;
import kr.ac.unist.apr.SwitchInfo;
import kr.ac.unist.apr.SwitchInfo.FileInfo;
import kr.ac.unist.apr.SwitchInfo.FuncInfo;
import kr.ac.unist.apr.SwitchInfo.LineInfo;
import kr.ac.unist.apr.TestValidator;
import edu.lu.uni.serval.utils.SuspiciousCodeParser.BuggyMethod;

import org.json.JSONObject;
import org.json.JSONArray;

/**
 * Abstract Fixer.
 * 
 * @author kui.liu
 *
 */
public abstract class AbstractFixer implements IFixer {
	public static String removeInnerClassFromSourcePath(String sourcePath) {
		String result=sourcePath;
		if (sourcePath.contains("$")){
			int index=sourcePath.indexOf('$');
			int extIndex=sourcePath.lastIndexOf('.');
			result=sourcePath.substring(0, index)+sourcePath.substring(extIndex);
		}
		return result;
	}
	
	private static Logger log = LoggerFactory.getLogger(AbstractFixer.class);
	
	public String metric = "Ochiai";          // Fault localization metric.
	protected String path = "";
	protected String buggyProject = "";     // The buggy project name.
	protected String defects4jPath;         // The path of local installed defects4j.
	public int minErrorTest;                // Number of failed test cases before fixing.
	protected int minErrorTestAfterFix = 0; // Number of failed test cases after fixing
	protected String fullBuggyProjectPath;  // The full path of the local buggy project.
	public String outputPath = "";          // Output path for the generated patches.
	public File suspCodePosFile = null;     // The file containing suspicious code positions localized by FL tools.
	protected DataPreparer dp;              // The needed data of buggy program for compiling and testing.
	protected int patchId=0;
	public String dataType="";
	public int fixedStatus = 0;
	
	private String failedTestCaseClasses = ""; // Classes of the failed test cases before fixing.
	// All specific failed test cases after testing the buggy project with defects4j command in Java code before fixing.
	protected List<String> failedTestStrList = new ArrayList<>();
	// All specific failed test cases after testing the buggy project with defects4j command in terminal before fixing.
	protected List<String> failedTestCasesStrList = new ArrayList<>();
	// The failed test cases after running defects4j command in Java code but not in terminal.
	private List<String> fakeFailedTestCasesList = new ArrayList<>();
	
	// Patch space tree
	protected List<FileInfo> switchInfos=new ArrayList<>();
	protected List<String> actualFailedTests;
	protected List<String> actualPassedTests;
	protected List<String> failedPassingTests;
	protected List<JsonInfo.Location> flList=new ArrayList<>();
	protected String cachePath;
	protected CacheInfo cacheInfo=new CacheInfo();
	// Information json of all generated patches
	protected JsonInfo jsonInfo;

	
	public AbstractFixer(String path, String projectName, int bugId, String defects4jPath) {
		this.path = path;
		this.buggyProject = projectName + "_" + bugId;
		fullBuggyProjectPath = path + buggyProject;
        this.defects4jPath = defects4jPath;

		this.cachePath=Configuration.cacheFile+"/"+buggyProject+"-cache.json";

		this.jsonInfo=new JsonInfo(buggyProject);
		// int compileResult = TestUtils.compileProjectWithDefects4j(fullBuggyProjectPath, this.defects4jPath);
        // if (compileResult == 1) {
        //     log.debug(buggyProject + " ---Fixer: fix fail because of compile fail! ");
        // }
		if (FileHelper.getAllFiles(path + buggyProject + PathUtils.getSrcPath(buggyProject).get(0), ".class").isEmpty()) {
			TestUtils.compileProjectWithDefects4j(path + buggyProject, defects4jPath);
		}
		minErrorTest = TestUtils.getFailTestNumInProject(path + buggyProject, defects4jPath, failedTestStrList);
		if (minErrorTest == Integer.MAX_VALUE) {
			TestUtils.compileProjectWithDefects4j(path + buggyProject, defects4jPath);
			minErrorTest = TestUtils.getFailTestNumInProject(path + buggyProject, defects4jPath, failedTestStrList);
		}
		log.info(buggyProject + " Failed Tests: " + this.minErrorTest);
		
		// Read paths of the buggy project.
		this.dp = new DataPreparer(path);
		dp.prepareData(buggyProject);
		
		readPreviouslyFailedTestCases();

		actualFailedTests=failedTestCasesStrList;
		actualPassedTests=new ArrayList<>(Arrays.asList(dp.testCases));
		failedPassingTests=new ArrayList<>();
		TestValidator testValid=new TestValidator(path,buggyProject,defects4jPath);
		try {
			testValid.checkoutBuggyVersion();
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

	}

	public AbstractFixer(String path, String metric, String projectName, int bugId, String defects4jPath) {
		this(path, projectName, bugId, defects4jPath);
		this.metric = metric;
	}
	
	private void readPreviouslyFailedTestCases() {
		String[] failedTestCases = FileHelper.readFile(Configuration.failedTestCasesFilePath + this.buggyProject + ".txt").split("\n");
		List<String> failedTestCasesList = new ArrayList<>();
		List<String> failed = new ArrayList<>();
		for (int index = 1, length = failedTestCases.length; index < length; index ++) {
			// - org.jfree.data.general.junit.DatasetUtilitiesTests::testBug2849731_2
			String failedTestCase = failedTestCases[index].trim();
			failed.add(failedTestCase);
			failedTestCase = failedTestCase.substring(failedTestCase.indexOf("-") + 1).trim();
			failedTestCasesStrList.add(failedTestCase);
			int colonIndex = failedTestCase.indexOf("::");
			if (colonIndex > 0) {
				failedTestCase = failedTestCase.substring(0, colonIndex);
			}
			if (!failedTestCasesList.contains(failedTestCase)) {
				this.failedTestCaseClasses += failedTestCase + " ";
				failedTestCasesList.add(failedTestCase);
			}
		}
		
		List<String> tempFailed = new ArrayList<>();
		tempFailed.addAll(this.failedTestStrList);
		tempFailed.removeAll(failed);
		// FIXME: Using defects4j command in Java code may generate some new failed-passing test cases.
		// We call them as fake failed-passing test cases.
		this.fakeFailedTestCasesList.addAll(tempFailed);
	}

	public List<SuspiciousPosition> readSuspiciousCodeFromFile() {
		File suspiciousFile = null;
		String suspiciousFilePath = "";
		if (this.suspCodePosFile == null) {
			suspiciousFilePath = Configuration.suspPositionsFilePath;
		} else {
			suspiciousFilePath = this.suspCodePosFile.getPath();
		}
		suspiciousFile = new File(suspiciousFilePath + "/" + this.buggyProject + "/" + this.metric.toLowerCase(Locale.ROOT) + ".txt");
		if (!suspiciousFile.exists()) {
			System.out.println("Cannot find the suspicious code position file." + suspiciousFile.getPath());
			suspiciousFile = new File(suspiciousFilePath + "/" + this.buggyProject + "/" + this.metric + ".txt");
		}
		
		List<SuspiciousPosition> suspiciousCodeList = new ArrayList<>();
		
		if (!suspiciousFile.exists()) {
			// Localize suspicious code positions.
			FL fl = new FL();
			fl.dp = this.dp;
			fl.locateSuspiciousCode(this.path, this.buggyProject, suspiciousFilePath + "/", this.metric);
			
			List<SuspiciousCode> suspStmts = fl.suspStmts;
			for (int index = 0, size = suspStmts.size(); index < size; index ++) {
				SuspiciousCode candidate = suspStmts.get(index);
				SuspiciousPosition sp = new SuspiciousPosition();
            	sp.classPath = candidate.getClassName();
                sp.lineNumber = candidate.lineNumber;
            	suspiciousCodeList.add(sp);
			}
		} else {
			try {
				FileReader fileReader = new FileReader(suspiciousFile);
				BufferedReader reader = new BufferedReader(fileReader);
				String line = null;
				int rank=0;
				while ((line = reader.readLine()) != null) {
					String[] elements = line.split("@");
					SuspiciousPosition sp = new SuspiciousPosition();
					sp.classPath = elements[0];
					sp.lineNumber = Integer.valueOf(elements[1]);
					sp.score=Double.valueOf(elements[2]);
					sp.rank=rank++;
					JsonInfo.Location newLoc=new JsonInfo.Location(sp.classPath, sp.lineNumber, Double.valueOf(elements[2]));
					jsonInfo.addFaultLocation(newLoc);
					this.flList.add(newLoc);
					suspiciousCodeList.add(sp);
				}
				reader.close();
				fileReader.close();
			}catch (Exception e){
				e.printStackTrace();
				log.debug("Reloading Localization Result...");
				return null;
			}
		}
		
		if (suspiciousCodeList.isEmpty()) return null;
		return suspiciousCodeList;
	}
	
	@Override
	public SuspCodeNode parseSuspiciousCode(SuspiciousPosition suspiciousCode) {
		String suspiciousClassName = suspiciousCode.classPath;
		int buggyLine = suspiciousCode.lineNumber;
		
		log.debug(suspiciousClassName + " ===" + buggyLine);
		if (suspiciousClassName.contains("$")) {
			suspiciousClassName = suspiciousClassName.substring(0, suspiciousClassName.indexOf("$"));
		}
		String suspiciousJavaFile = suspiciousClassName.replace(".", "/") + ".java";
		
		suspiciousClassName = suspiciousJavaFile.substring(0, suspiciousJavaFile.length() - 5).replace("/", ".");
		
		String filePath = dp.srcPath + suspiciousJavaFile;
		SuspiciousCodeParser scp = new SuspiciousCodeParser();
		scp.parseSuspiciousCode(new File(filePath), buggyLine);
		
		ITree suspCodeAstNode = scp.getSuspiciousCodeAstNode();
		String suspCodeStr = scp.getSuspiciousCodeStr();
		if (suspCodeAstNode == null || suspCodeStr == null) {
			log.debug("Failed to identify the buggy statement in: " + suspiciousClassName + " --- " + buggyLine);
			return null;
		}
		log.debug("Suspicious Code: \n" + suspCodeStr);
		
		int startPos = suspCodeAstNode.getPos();
		int endPos = startPos + suspCodeAstNode.getLength();
		
		File targetJavaFile = new File(FileUtils.getFileAddressOfJava(dp.srcPath, suspiciousClassName));
        File targetClassFile = new File(FileUtils.getFileAddressOfClass(dp.classPath, suspiciousClassName));
        File javaBackup = new File(FileUtils.tempJavaPath(suspiciousClassName,  this.dataType + "/" + this.buggyProject));
        File classBackup = new File(FileUtils.tempClassPath(suspiciousClassName, this.dataType + "/" + this.buggyProject));
        try {
        	if (javaBackup.exists()) javaBackup.delete();
        	if (classBackup.exists()) classBackup.delete();
			Files.copy(targetJavaFile.toPath(), javaBackup.toPath());
			Files.copy(targetClassFile.toPath(), classBackup.toPath());
		} catch (IOException e) {
			e.printStackTrace();
		}
        
        SuspCodeNode scn = new SuspCodeNode(javaBackup, classBackup, targetJavaFile, targetClassFile, 
                startPos, endPos, suspCodeAstNode, suspCodeStr, suspiciousJavaFile, buggyLine,suspiciousCode.score,suspiciousCode.rank);
        return scn;
	}

	protected List<Patch> triedPatchCandidates = new ArrayList<>();
	private Map<String,Integer> countOfLocationMutator=new HashMap<>();

	protected void addPatchesToInfo(List<Patch> patchCandidates,SuspCodeNode scn){
		log.debug("Add "+Integer.toString(patchCandidates.size())+ " patches: File: "+scn.suspiciousJavaFile+", Line: "+Integer.toString(scn.buggyLine));
		for (Patch patch : patchCandidates) {
			patch.buggyFileName = scn.suspiciousJavaFile;
			if (this.triedPatchCandidates.contains(patch)) {
				try {
					scn.targetJavaFile.delete();
					scn.targetClassFile.delete();
					Files.copy(scn.javaBackup.toPath(), scn.targetJavaFile.toPath(),StandardCopyOption.REPLACE_EXISTING);
					Files.copy(scn.classBackup.toPath(), scn.targetClassFile.toPath(),StandardCopyOption.REPLACE_EXISTING);
				} catch (IOException e) {
					e.printStackTrace();
				}
				continue;
			}
			patchId++;
			// this.triedPatchCandidates.add(patch);
			String mutatorName=patch.mutator.getSimpleName();

			// Save patched source file to temp dir
			File tempDir=new File("d4j");
			if(!tempDir.exists()) tempDir.mkdir();
			tempDir=new File("d4j/"+buggyProject);
			if(!tempDir.exists()) tempDir.mkdir();
			tempDir=new File("d4j/"+buggyProject+"/"+Integer.toString(scn.rank));
			if(!tempDir.exists()) tempDir.mkdir();
			tempDir=new File("d4j/"+buggyProject+"/"+Integer.toString(scn.rank)+"/"+mutatorName);
			if(!tempDir.exists()) tempDir.mkdir();

			if (!countOfLocationMutator.containsKey(mutatorName)) countOfLocationMutator.put(mutatorName, 0);
			String fixedDir="d4j/"+buggyProject+"/"+Integer.toString(scn.rank)+"/"+
						mutatorName+"/"+Integer.toString(patchId)+"/";
			String fixedPath=fixedDir+scn.suspiciousJavaFile;
			tempDir=new File(fixedDir);
			if(!tempDir.exists()) tempDir.mkdir();

			String file=(PathUtils.getSrcPath(buggyProject).get(2)).substring(1)+scn.suspiciousJavaFile;
			file=removeInnerClassFromSourcePath(file);
			int line=scn.buggyLine;
			int startPos=scn.startPos;
			int endPos=scn.endPos;
			double score=scn.flScore;

			FileInfo fileInfo=null;
			// Find current file
			for (FileInfo tempFileInfo:switchInfos){
				if (tempFileInfo.fileName.equals(file)){
					fileInfo=tempFileInfo;
					break;
				}
			}
			if (fileInfo==null){
				fileInfo=new FileInfo(file,(scn.targetClassFile.getPath().replaceFirst(fullBuggyProjectPath,"")).substring(1));
				log.debug(fileInfo.className);
				switchInfos.add(fileInfo);
			}

			// Find current function
			Map<String,Integer[]> lines=MethodFinder.infos.get(file);
			String function="no_function:"+Integer.toString(line);
			for (String funcName:lines.keySet()){
				if (lines.get(funcName)[0]<=line && lines.get(funcName)[1]>=line){
					function=funcName;
					break;
				}
			}
			FuncInfo funcInfo=null;
			for (FuncInfo tempFuncInfo:fileInfo.funcInfos){
				if (tempFuncInfo.funcName.equals(function)){
					funcInfo=tempFuncInfo;
					break;
				}
			}
			if (funcInfo==null){
				funcInfo=new FuncInfo(function);
				fileInfo.funcInfos.add(funcInfo);
			}

			LineInfo lineInfo=null;
			for (LineInfo tempLineInfo:funcInfo.lineInfos){
				if (tempLineInfo.line==line){
					lineInfo=tempLineInfo;
					break;
				}
			}
			if (lineInfo==null){
				lineInfo=new LineInfo(line);
				lineInfo.id=scn.rank;
				funcInfo.lineInfos.add(lineInfo);
			}

			List<String> dirs=Arrays.asList(fixedPath.split("/"));
			String sourceFile=dirs.get(dirs.size()-1);
			sourceFile=removeInnerClassFromSourcePath(sourceFile);

			SwitchInfo newInfo=new SwitchInfo();
			newInfo.startOffset=startPos;
			newInfo.endOffset=endPos;
			newInfo.fixedSourcePath=Integer.toString(scn.rank)+"/"+
							mutatorName+"/"+Integer.toString(patchId)+"/"+sourceFile;
			newInfo.score=score;
			newInfo.mutator=patch.mutator;
			newInfo.id=patchId;
			patch.id=patchId;
			lineInfo.switchInfos.add(newInfo);

			tempDir=new File(fixedDir);
			if(!tempDir.exists()) tempDir.mkdir();

			addPatchCodeToFile(scn, patch, fixedDir+sourceFile);
			jsonInfo.addPatchRanking(newInfo.fixedSourcePath);
		}
	}

	private void addPatchCodeToFile(SuspCodeNode scn, Patch patch,String outputPath) {
		String javaCode = FileHelper.readFile(scn.javaBackup);
        
		String fixedCodeStr1 = patch.getFixedCodeStr1();
		String fixedCodeStr2 = patch.getFixedCodeStr2();
		int exactBuggyCodeStartPos = patch.getBuggyCodeStartPos();
		int exactBuggyCodeEndPos = patch.getBuggyCodeEndPos();
		String patchCode = fixedCodeStr1;
		boolean needBuggyCode = false;
		if (exactBuggyCodeEndPos > exactBuggyCodeStartPos) {
			if ("MOVE-BUGGY-STATEMENT".equals(fixedCodeStr2)) {
				// move statement position.
			} else if (exactBuggyCodeStartPos != -1 && exactBuggyCodeStartPos < scn.startPos) {
				// Remove the buggy method declaration.
			} else {
				needBuggyCode = true;
				if (exactBuggyCodeStartPos == 0) {
					// Insert the missing override method, the buggy node is TypeDeclaration.
					int pos = scn.suspCodeAstNode.getPos() + scn.suspCodeAstNode.getLength() - 1;
					for (int i = pos; i >= 0; i --) {
						if (javaCode.charAt(i) == '}') {
							exactBuggyCodeStartPos = i;
							exactBuggyCodeEndPos = i + 1;
							break;
						}
					}
				} else if (exactBuggyCodeStartPos == -1 ) {
					// Insert generated patch code before the buggy code.
					exactBuggyCodeStartPos = scn.startPos;
					exactBuggyCodeEndPos = scn.endPos;
				} else {
					// Insert a block-held statement to surround the buggy code
				}
			}
		} else if (exactBuggyCodeStartPos == -1 && exactBuggyCodeEndPos == -1) {
			// Replace the buggy code with the generated patch code.
			exactBuggyCodeStartPos = scn.startPos;
			exactBuggyCodeEndPos = scn.endPos;
		} else if (exactBuggyCodeStartPos == exactBuggyCodeEndPos) {
			// Remove buggy variable declaration statement.
			exactBuggyCodeStartPos = scn.startPos;
		}
		
		patch.setBuggyCodeStartPos(exactBuggyCodeStartPos);
		patch.setBuggyCodeEndPos(exactBuggyCodeEndPos);
        String buggyCode;
		try {
			buggyCode = javaCode.substring(exactBuggyCodeStartPos, exactBuggyCodeEndPos);
			if (needBuggyCode) {
	        	patchCode += buggyCode;
	        	if (fixedCodeStr2 != null) {
	        		patchCode += fixedCodeStr2;
	        	}
	        }
			
			if (outputPath.equals("")){
				// Save to source code, if output path not specified
				File newFile = new File(scn.targetJavaFile.getAbsolutePath() + ".temp");
				String patchedJavaFile = javaCode.substring(0, exactBuggyCodeStartPos) + patchCode + javaCode.substring(exactBuggyCodeEndPos);
				FileHelper.outputToFile(newFile, patchedJavaFile, false);
				newFile.renameTo(scn.targetJavaFile);
			}
			else{
				File newFile = new File(outputPath);
				String patchedJavaFile = javaCode.substring(0, exactBuggyCodeStartPos) + patchCode + javaCode.substring(exactBuggyCodeEndPos);
				FileHelper.outputToFile(newFile, patchedJavaFile, false);
			}
		} catch (StringIndexOutOfBoundsException e) {
			log.debug(exactBuggyCodeStartPos + " ==> " + exactBuggyCodeEndPos + " : " + javaCode.length());
			e.printStackTrace();
			buggyCode = "===StringIndexOutOfBoundsException===";
		}
        
        patch.setBuggyCodeStr(buggyCode);
        patch.setFixedCodeStr1(patchCode);
	}
	
	class SuspCodeNode {

        public String projectId;
		public File javaBackup;
		public File classBackup;
		public File targetJavaFile;
		public File targetClassFile;
		public int startPos;
		public int endPos;
		public ITree suspCodeAstNode;
		public String suspCodeStr;
		public String suspiciousJavaFile;
        public int buggyLine;
        
		public double flScore;
    	public int rank;
		
		public SuspCodeNode(File javaBackup, File classBackup, File targetJavaFile, File targetClassFile, int startPos,
				int endPos, ITree suspCodeAstNode, String suspCodeStr, String suspiciousJavaFile, int buggyLine,double flScore,int rank) {
			this.javaBackup = javaBackup;
			this.classBackup = classBackup;
			this.targetJavaFile = targetJavaFile;
			this.targetClassFile = targetClassFile;
			this.startPos = startPos;
			this.endPos = endPos;
			this.suspCodeAstNode = suspCodeAstNode;
			this.suspCodeStr = suspCodeStr;
			this.suspiciousJavaFile = suspiciousJavaFile;
			this.buggyLine = buggyLine;

			this.flScore=flScore;
			this.rank=rank;
		}

		@Override
		public boolean equals(Object obj) {
			if (obj == null) return false;
			if (obj instanceof SuspCodeNode) {
				SuspCodeNode suspN = (SuspCodeNode) obj;
				if (startPos != suspN.startPos) return false;
				if (endPos != suspN.endPos) return false;
				if (suspiciousJavaFile.equals(suspN.suspiciousJavaFile)) return true;
			}
			return false;
		}
	}
}
