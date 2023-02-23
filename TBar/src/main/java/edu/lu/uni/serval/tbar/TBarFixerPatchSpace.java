package edu.lu.uni.serval.tbar;

import edu.lu.uni.serval.tbar.config.Configuration;
import edu.lu.uni.serval.tbar.context.ContextReader;
import edu.lu.uni.serval.tbar.fixpatterns.*;
import edu.lu.uni.serval.tbar.fixtemplate.FixTemplate;
import edu.lu.uni.serval.tbar.info.Patch;
import edu.lu.uni.serval.tbar.json.MethodInfoUtils;
import edu.lu.uni.serval.tbar.json.PatchesLogs;
import edu.lu.uni.serval.tbar.json.util.PatchSpaceUtils;
import edu.lu.uni.serval.tbar.utils.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.*;

public class TBarFixerPatchSpace extends TBarFixer {

    private final static Logger log = LoggerFactory.getLogger(TBarFixerPatchSpace.class);
    private final PatchesLogs jsonLogs = new PatchesLogs();

    private int totalPatches = 0;
    private final ArrayList<String> failedMethods = new ArrayList<>();

    public TBarFixerPatchSpace(String path, String projectName, int bugId, String defects4jPath) {
        super(path, projectName, bugId, defects4jPath);
        this.jsonLogs.setProjectName(projectName + "_" + bugId);
    }

    @Override
    public void fixProcess() {
        // Read paths of the buggy project.
        if (!dp.validPaths) return;

        Configuration.TEMP_FILES_PATH = fullBuggyProjectPath + "/" + Configuration.TEMP_FILES_PATH;
        Configuration.TEMP_PATCHES_FILES_PATH = fullBuggyProjectPath + "/" + Configuration.TEMP_PATCHES_FILES_PATH;

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

        // Json failing test cases
//        readFailingCases();
        // Json passing test cases
//        readPassingCases();
        // Json passing and failing tests
        readPassingAndFailingTests();

        List<SuspCodeNode> triedSuspNode = new ArrayList<>();

        log.info("======= TBar: Start to fix suspicious code ======");
        for (int i = 0; i < suspiciousCodeList.size(); i++) {
            SuspiciousPosition suspiciousCode = suspiciousCodeList.get(i);
            List<SuspCodeNode> scns = parseSuspiciousCode(suspiciousCode);

            // Json logs
            this.jsonLogs.addPriority(suspiciousCode.classPath, suspiciousCode.lineNumber, suspiciousCode.score);

            if (scns == null) continue;

            for (int j = 0; j < scns.size(); j++) {
                SuspCodeNode scn = scns.get(j);
                scn.score = suspiciousCode.score;
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
        // Json logs
        createJsonLogs();

        log.debug("Not function level for JSON:");
        for (String fail: failedMethods) {
            System.out.println(fail);
        }

        log.info("totally created " + totalPatches + " patches");
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
        saveGeneratedPatches(patchCandidates, scn, prefix, ft.getClass().getSimpleName());
    }

    private void saveGeneratedPatches(List<Patch> patchCandidates, SuspCodeNode scn, String prefix, String fixname) {
        for (int i = 0; i < patchCandidates.size(); i++) {
            Patch patch = patchCandidates.get(i);
            patch.buggyFileName = scn.suspiciousJavaFile;
            totalPatches++;
            String preprefix = prefix + "_" + totalPatches + "_" + i;
            String patchLocation = null;
            try {
                patchLocation = addPatchCodeToFile(scn, patch, preprefix, fixname);
                if (patchLocation != null) {
                    String pathPrefix = Configuration.OUTPUT_DIR;
                    if (pathPrefix == null) {
                        pathPrefix = Configuration.TEMP_PATCHES_FILES_PATH;
                    }
                    patchLocation = patchLocation.substring((pathPrefix + this.buggyProject).length());
                }
            } catch (IllegalAccessException e) {
                e.printStackTrace();
            }
            if (patchLocation == null) {
                log.error("SKIPPING the patch " + fixname + " " + preprefix);
                totalPatches--;
                // rollbackFiles(scn);
                continue;
            }

            String buggyCode = patch.getBuggyCodeStr();
            if ("===StringIndexOutOfBoundsException===".equals(buggyCode)) continue;
            String patchCode = patch.getFixedCodeStr1();
//            log.info("Buggy Code: \n" + buggyCode + "\n Patched Code: \n" + patchCode);

//            try {
//                testPatch(patch, scn, prefix + fixname);
//            } catch (IllegalArgumentException e) {
//                continue;
//            } finally {
//                rollbackFiles(scn);
//            }

            // Json logs
            int startPosition = patch.getBuggyCodeStartPos();
            int endPosition = patch.getBuggyCodeEndPos();
            String javafile = scn.targetJavaFile.getAbsolutePath();
            int startLine = PatchSpaceUtils.getLineNumberOnPosition(javafile, startPosition);
            int endLine = PatchSpaceUtils.getLineNumberOnPosition(javafile, endPosition);
//            log.info("Line pair: " + startLine + ":" + endLine);
            addLineJsonLogs(scn, fixname, patchLocation, startLine, endLine, startPosition, endPosition);
            addMutationRank(patchLocation, totalPatches);
        }
    }

    private String addPatchCodeToFile(
            SuspCodeNode scn,
            Patch patch,
            String preprefix,
            String fixname
    ) throws IllegalAccessException {
        String javaCode = FileHelper.readFile(scn.javaBackup);
        String fixedCodeStr1 = patch.getFixedCodeStr1();
        String fixedCodeStr2 = patch.getFixedCodeStr2();
        int exactBuggyCodeStartPos = patch.getBuggyCodeStartPos();
        int exactBuggyCodeEndPos = patch.getBuggyCodeEndPos();
        String patchCode = fixedCodeStr1;
        boolean needBuggyCode = false;
        if (exactBuggyCodeEndPos > exactBuggyCodeStartPos) {
            if ("MOVE-BUGGY-STATEMENT".equals(fixedCodeStr2)) {
                // move statement position. Todo
            } else if (exactBuggyCodeStartPos != -1 && exactBuggyCodeStartPos < scn.startPos) {
                // Remove the buggy method declaration. Todo
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
                    // Insert a block-held statement to surround the buggy code Todo
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
        File tempNewFile = null;
        try {
            buggyCode = javaCode.substring(exactBuggyCodeStartPos, exactBuggyCodeEndPos);
            if (needBuggyCode) {
                patchCode += buggyCode;
                if (fixedCodeStr2 != null) {
                    patchCode += fixedCodeStr2;
                }
            }
            String patchSuffix = preprefix + "_" + fixname;
//            tempNewFile = new File(
//                    Configuration.TEMP_PATCHES_FILES_PATH + this.buggyProject + "/" + patchSuffix + "/" + scn.targetJavaFile.getName()
//            );
            String pathPrefix = Configuration.OUTPUT_DIR;
            if (pathPrefix == null) {
                pathPrefix = Configuration.TEMP_PATCHES_FILES_PATH;
            }
            tempNewFile = new File(
                    pathPrefix + this.buggyProject + "/" + patchSuffix + "/" + scn.targetJavaFile.getName()
            );
            String patchedJavaCode = javaCode
                    .substring(0, exactBuggyCodeStartPos) + patchCode + javaCode.substring(exactBuggyCodeEndPos);
            FileHelper.outputToFile(tempNewFile, patchedJavaCode, false);
            try {
                tempNewFile.createNewFile();
            } catch (Exception e) {
                log.error("Couldn't create new file:", e);
            }

            // Insert patch to target project
//            File patchedFile = new File(scn.targetJavaFile.getAbsolutePath() + ".temp");
//            FileHelper.outputToFile(patchedFile, patchedJavaCode, false);
//            if (!patchedFile.renameTo(scn.targetJavaFile)) {
//                log.error("Couldn't insert patch to target project");
//                throw new IllegalAccessException("Patch is not inserted");
//            }

        } catch (StringIndexOutOfBoundsException e) {
            log.debug(exactBuggyCodeStartPos + " ==> " + exactBuggyCodeEndPos + " : " + javaCode.length());
            e.printStackTrace();
            buggyCode = "===StringIndexOutOfBoundsException===";
        }

        patch.setBuggyCodeStr(buggyCode);
        patch.setFixedCodeStr1(patchCode);

        if (tempNewFile == null) return null;
        return tempNewFile.getAbsolutePath();
    }

    private void readPassingCases() {
        System.out.println(fullBuggyProjectPath + "/" + "all-tests.txt");
        String[] allTests = FileHelper.readFile(fullBuggyProjectPath + "/" + "all-tests.txt").split("\n");
        List<String> passingTests = new ArrayList<>();
        for (String failingTest: this.failedTestStrList) {
            String failingTestIden = failingTest.split("::")[1] + "(";
            for (String test: allTests) {
                if (!test.contains(failingTestIden)) {
                    passingTests.add(test);
                }
            }
        }
        this.jsonLogs.addPassingTestCases(passingTests);
    }

//    private void readPassingAndFailingTests() {
//        System.out.println(fullBuggyProjectPath + "/" + "all_tests");
//        String[] allTests = FileHelper.readFile(fullBuggyProjectPath + "/" + "all_tests").split("\n");
//        List<String> passingTests = new ArrayList<>();
//        List<String> failingTests = new ArrayList<>();
//        for (String failingTest: this.failedTestStrList) {
//            String failingTestIden = failingTest.split("::")[1] + "(";
//            for (String test: allTests) {
//                if (!test.contains(failingTestIden)) {
//                    passingTests.add(test);
//                } else {
//                    failingTests.add(test);
//                }
//            }
//        }
//        this.jsonLogs.addPassingTestCases(passingTests);
//        this.jsonLogs.addFailingTestCases(failingTests);
//    }

    private void readPassingAndFailingTests() {
        System.out.println(fullBuggyProjectPath + "/" + "all-tests.txt");
        String[] allTests = FileHelper.readFile(fullBuggyProjectPath + "/" + "all-tests.txt").split("\n");
        Set<String> passingTests = new HashSet<>();
        Set<String> failingTests = new HashSet<>();
        Set<String> failedPassingTests = new HashSet<>();
        System.out.println(this.fakeFailedTestCasesList);
        System.out.println(this.failedTestCasesStrList);
        for (String test: allTests) {
            if (test.trim().equals("")) continue;
            if (test.split("\\)").length > 2) {
                for (String subTest: test.split("\\)")) {
                    if (subTest.trim().equals("")) continue;
                    String preprocessTest = subTest.substring(subTest.indexOf("(") + 1);
                    String methodTest = subTest.substring(0, subTest.indexOf("("));
                    String ref_test = preprocessTest + "::" + methodTest;
                    if (this.failedTestCasesStrList.contains(ref_test)) {
                        failingTests.add(ref_test);
                    } else if (this.fakeFailedTestCasesList.contains(ref_test)) {
                        failedPassingTests.add(ref_test);
                    } else {
                        passingTests.add(ref_test);
                    }
                }
            }
            String preprocessTest = test.substring(test.indexOf("(") + 1, test.indexOf(")"));
            String methodTest = test.substring(0, test.indexOf("("));
            String ref_test = preprocessTest + "::" + methodTest;
            if (this.failedTestCasesStrList.contains(ref_test)) {
                failingTests.add(ref_test);
            } else if (this.fakeFailedTestCasesList.contains(ref_test)) {
                failedPassingTests.add(ref_test);
            } else {
                passingTests.add(ref_test);
            }
        }

        this.jsonLogs.addPassingTestCases(new ArrayList<>(passingTests));
        this.jsonLogs.addFailingTestCases(new ArrayList<>(failingTests));
        this.jsonLogs.addFailedPassingTests(new ArrayList<>(failedPassingTests));
    }

    private void createJsonLogs() {
        try {
            String pathPrefix = Configuration.OUTPUT_DIR;
            if (pathPrefix == null) {
                pathPrefix = fullBuggyProjectPath;
            } else {
                pathPrefix = Configuration.OUTPUT_DIR + this.buggyProject;
            }
            File logs = new File(pathPrefix + "/" + Configuration.JSON_LOG_PATH);
            if (!logs.getParentFile().exists()) {
                logs.getParentFile().mkdirs();
            }
            if (!logs.createNewFile()) {
                log.info("Couldn't create json logs ;(, changing existing logs file");
            }
            FileWriter writer = new FileWriter(logs);
            BufferedWriter buffer = new BufferedWriter(writer);
            buffer.write(this.jsonLogs.createJsonObject());
            buffer.flush();
            writer.close();
            buffer.close();
        } catch (IOException e) {
            log.error(e.getMessage());
        }
    }

    private void addLineJsonLogs(
            SuspCodeNode scn,
            String fixname,
            String patchLocation,
            int startLine, int endLine,
            int startPosition, int endPosition
    ) {
        String javafile = scn.targetJavaFile.getAbsolutePath();
        javafile = javafile.substring(Configuration.WORK_DIR.length());
        String classFile = scn.targetClassFile.getAbsolutePath();
        classFile = classFile.substring(Configuration.WORK_DIR.length());
        try {
            MethodInfoUtils.MethodBeam beam = MethodInfoUtils.validateMethodLineRange(
                    scn.buggyLine, scn.targetJavaFile.getAbsolutePath()
            );
            jsonLogs.addLine(javafile, scn.buggyLine, fixname, patchLocation, startPosition, endPosition, scn.score);
            jsonLogs.addJavaToClassfile(javafile, classFile);
            if (beam == null) throw new IllegalArgumentException("Method not found");
            addFunctionJsonLogs(scn, beam.start);
        } catch (Exception e) {
            e.printStackTrace();
            failedMethods.add(fixname + " " + startLine + ":" + endLine + " " + scn.targetJavaFile.getPath());
        }
    }

    private void addFunctionJsonLogs(SuspCodeNode scn, int buggyLine) {
        try {
            MethodInfoUtils.MethodBeam beam = MethodInfoUtils.getMethodFromLine(
                    buggyLine, scn.targetJavaFile.getAbsolutePath());
            if (beam == null) throw new IllegalArgumentException("Method not found");
            String javafile = scn.targetJavaFile.getAbsolutePath();
            javafile = javafile.substring(Configuration.WORK_DIR.length());
            this.jsonLogs.addMethodMutation(
                javafile,
                beam.name, beam.desc,
                beam.start, beam.end
            );
        } catch (Exception e) {
            // Todo
        }
    }

    private void addMutationRank(String location, int rank) {
        this.jsonLogs.addRanking(location, rank);
    }

    private void saveRunningTime(String projectId, long time) {
        try {
            File timeLog = new File("running-times.csv");
            timeLog.createNewFile();
            FileWriter writer = new FileWriter(timeLog, true);
            BufferedWriter buffer = new BufferedWriter(writer);
            buffer.write(projectId + "," + time);
            buffer.newLine();
            buffer.flush();
            writer.close();
            buffer.close();
        } catch (Exception e) {
            log.error(e.getMessage());
        }
    }
}
