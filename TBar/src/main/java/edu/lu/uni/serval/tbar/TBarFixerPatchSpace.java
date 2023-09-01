package edu.lu.uni.serval.tbar;

import edu.lu.uni.serval.tbar.config.Configuration;
import edu.lu.uni.serval.tbar.context.ContextReader;
import edu.lu.uni.serval.tbar.fixpatterns.*;
import edu.lu.uni.serval.tbar.fixtemplate.FixTemplate;
import edu.lu.uni.serval.tbar.info.Patch;
import edu.lu.uni.serval.tbar.utils.*;
import kr.ac.unist.apr.MethodFinder;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.*;

public class TBarFixerPatchSpace extends TBarFixer {

    private final static Logger log = LoggerFactory.getLogger(TBarFixerPatchSpace.class);

    private int totalPatches = 0;
    private final ArrayList<String> failedMethods = new ArrayList<>();

    public TBarFixerPatchSpace(String path, String projectName, int bugId, String defects4jPath) {
        super(path, projectName, bugId, defects4jPath);
    }

    @Override
    public void fixProcess() {
        // Read paths of the buggy project.
        if (!dp.validPaths) return;

        Configuration.TEMP_FILES_PATH = fullBuggyProjectPath + "/" + Configuration.TEMP_FILES_PATH;
        Configuration.TEMP_PATCHES_FILES_PATH = fullBuggyProjectPath + "/" + Configuration.TEMP_PATCHES_FILES_PATH;

        MethodFinder.parseFiles(fullBuggyProjectPath+PathUtils.getSrcPath(buggyProject).get(2),buggyProject);
        // Read suspicious positions.
        List<SuspiciousPosition> suspiciousCodeList;
        if (granularity == Granularity.Line) {
            // It assumes that the line-level bug positions are known.
            suspiciousCodeList = readKnownBugPositionsFromFile();
        } else if (granularity == Granularity.File) {
            // It assumes that the file-level bug positions are known.
            List<String> buggyFileList = readKnownFileLevelBugPositions();
            suspiciousCodeList = readSuspiciousCodeFromFile(buggyFileList);
        } else {
            suspiciousCodeList = readSuspiciousCodeFromFile();
        }

        if (suspiciousCodeList == null) return;

        List<SuspCodeNode> triedSuspNode = new ArrayList<>();

        log.info("======= TBar: Start to fix suspicious code ======");
        for (int i = 0; i < suspiciousCodeList.size(); i++) {
            SuspiciousPosition suspiciousCode = suspiciousCodeList.get(i);
            List<SuspCodeNode> scns = parseSuspiciousCode(suspiciousCode);

            if (scns == null) continue;

            for (int j = 0; j < scns.size(); j++) {
                SuspCodeNode scn = scns.get(j);
//				log.debug(scn.suspCodeStr);
                if (triedSuspNode.contains(scn)) continue;
                triedSuspNode.add(scn);

                // Parse context information of the suspicious code.
                List<Integer> contextInfoList = readAllNodeTypes(scn.suspCodeAstNode);
                List<Integer> distinctContextInfo = new ArrayList<>();
                for (Integer contInfo : contextInfoList) {
                    if (!distinctContextInfo.contains(contInfo) && !Checker.isBlock(contInfo)) {
                        distinctContextInfo.add(contInfo);
                    }
                }
//				List<Integer> distinctContextInfo = contextInfoList.stream().distinct().collect(Collectors.toList());

                // Match fix templates for this suspicious code with its context information.
                String prefix = i + "_" + j;
                long startTime=Calendar.getInstance().getTimeInMillis();
                fixWithMatchedFixTemplates(scn, distinctContextInfo, prefix);
                log.info("Generation time: "+Long.toString(Calendar.getInstance().getTimeInMillis()-startTime));
            }
        }
        log.info("=======TBar: Finish off fixing======");

        log.info("totally created " + totalPatches + " patches");
        jsonInfo.setSwitchInfos(switchInfos);
        jsonInfo.saveToFile(buggyProject);
        // FileHelper.deleteDirectory(Configuration.TEMP_FILES_PATH + this.dataType + "/" + this.buggyProject);
    }

    public void fixWithMatchedFixTemplates(SuspCodeNode scn, List<Integer> distinctContextInfo, String prefix) {
        // generate patches with fix templates of TBar.
        // FixTemplate ft = null;
        // FixPattern pattern = Configuration.transformers.get(0);
        FixTemplate ft = null;

        if (!Checker.isMethodDeclaration(scn.suspCodeAstNode.getType())) {
            boolean nullChecked = false;
            boolean typeChanged = false;
            boolean methodChanged = false;
            boolean operator = false;

            for (Integer contextInfo : distinctContextInfo) {
                if (Checker.isCastExpression(contextInfo)) {
                    ft = new ClassCastChecker();
                    if (!typeChanged) {
                        generateAndValidatePatches(ft, scn, prefix);
                        typeChanged = true;
                        ft = new DataTypeReplacer();
                    }
                } else if (Checker.isClassInstanceCreation(contextInfo)) {
//					ft = new CNIdiomNoSuperCall();
//					if (isTestFixPatterns) dataType = readDirectory() + "/CNIdiomNoSuperCall";
                    if (!methodChanged) {
//						generateAndValidatePatches(ft, scn);
//						if (!isTestFixPatterns && this.minErrorTest == 0) return;
                        methodChanged = true;
                        ft = new MethodInvocationMutator();
                    }
                } else if (Checker.isIfStatement(contextInfo) || Checker.isDoStatement(contextInfo) || Checker.isWhileStatement(contextInfo)) {
                    if (Checker.isInfixExpression(scn.suspCodeAstNode.getChild(0).getType()) && !operator) {
                        operator = true;
                        ft = new OperatorMutator(0);
                        generateAndValidatePatches(ft, scn, prefix);
                    }
                    ft = new ConditionalExpressionMutator(2);
                } else if (Checker.isConditionalExpression(contextInfo)) {
                    ft = new ConditionalExpressionMutator(0);
                } else if (Checker.isCatchClause(contextInfo) || Checker.isVariableDeclarationStatement(contextInfo)) {
                    if (!typeChanged) {
                        ft = new DataTypeReplacer();
                        typeChanged = true;
                    }
                } else if (Checker.isInfixExpression(contextInfo)) {
                    ft = new ICASTIdivCastToDouble();
                    generateAndValidatePatches(ft, scn, prefix);
                    if (!operator) {
                        operator = true;
                        ft = new OperatorMutator(0);
                        generateAndValidatePatches(ft, scn, prefix);
                    }

                    ft = new ConditionalExpressionMutator(1);
                    generateAndValidatePatches(ft, scn, prefix);
                    ft = new OperatorMutator(4);
                } else if (Checker.isBooleanLiteral(contextInfo) || Checker.isNumberLiteral(contextInfo) || Checker.isCharacterLiteral(contextInfo)|| Checker.isStringLiteral(contextInfo)) {
                    ft = new LiteralExpressionMutator();
                } else if (Checker.isMethodInvocation(contextInfo) || Checker.isConstructorInvocation(contextInfo) || Checker.isSuperConstructorInvocation(contextInfo)) {
                    if (!methodChanged) {
                        ft = new MethodInvocationMutator();
                        methodChanged = true;
                    }

                    if (Checker.isMethodInvocation(contextInfo)) {
                        if (ft != null) {
                            generateAndValidatePatches(ft, scn, prefix);
                        }
                        ft = new NPEqualsShouldHandleNullArgument();
                        generateAndValidatePatches(ft, scn, prefix);
                        ft = new RangeChecker(false);
                    }
                } else if (Checker.isAssignment(contextInfo)) {
                    ft = new OperatorMutator(2);
                } else if (Checker.isInstanceofExpression(contextInfo)) {
                    ft = new OperatorMutator(5);
                } else if (Checker.isArrayAccess(contextInfo)) {
                    ft = new RangeChecker(true);
                } else if (Checker.isReturnStatement(contextInfo)) {
                    String returnType = ContextReader.readMethodReturnType(scn.suspCodeAstNode);
                    if ("boolean".equalsIgnoreCase(returnType)) {
                        ft = new ConditionalExpressionMutator(2);
                    } else {
                        ft = new ReturnStatementMutator(returnType);
                    }
                } else if (Checker.isSimpleName(contextInfo) || Checker.isQualifiedName(contextInfo)) {
                    ft = new VariableReplacer();

                    if (!nullChecked) {
                        generateAndValidatePatches(ft, scn, prefix);
                        nullChecked = true;
                        ft = new NullPointerChecker();
                    }
                }
                if (ft != null) {
                    generateAndValidatePatches(ft, scn, prefix);
                }
                ft = null;
            }

            if (!nullChecked) {
                nullChecked = true;
                ft = new NullPointerChecker();
                generateAndValidatePatches(ft, scn, prefix);
            }

            ft = new StatementMover();
            generateAndValidatePatches(ft, scn, prefix);

            ft = new StatementRemover();
            generateAndValidatePatches(ft, scn, prefix);

            ft = new StatementInserter();
            generateAndValidatePatches(ft, scn, prefix);
        } else {
            ft = new StatementRemover();
            generateAndValidatePatches(ft, scn, prefix);
        }
    }

    @Override
    protected void generateAndValidatePatches(FixTemplate ft, SuspCodeNode scn) {
        ft.setSuspiciousCodeStr(scn.suspCodeStr);
        ft.setSuspiciousCodeTree(scn.suspCodeAstNode);
        if (scn.javaBackup == null) ft.setSourceCodePath(dp.srcPath);
        else ft.setSourceCodePath(dp.srcPath, scn.javaBackup);
        ft.setDictionary(dic);
        ft.generatePatches();
        List<Patch> patchCandidates = ft.getPatches();
//		System.out.println(dataType + " ====== " + patchCandidates.size());

        // Test generated patches.
//        if (patchCandidates.isEmpty()) return;
//        saveGeneratedPatches(patchCandidates, scn);
    }

    protected void generateAndValidatePatches(FixTemplate ft, SuspCodeNode scn, String prefix) {
        ft.setSuspiciousCodeStr(scn.suspCodeStr);
        ft.setSuspiciousCodeTree(scn.suspCodeAstNode);
        if (scn.javaBackup == null) ft.setSourceCodePath(dp.srcPath);
        else ft.setSourceCodePath(dp.srcPath, scn.javaBackup);
        ft.setDictionary(this.dic);
        ft.generatePatches();
        List<Patch> patchCandidates = ft.getPatches();
        // Test generated patches.
        if (patchCandidates.isEmpty()) return;
        addPatchesToInfo(patchCandidates, scn);
    }
}
