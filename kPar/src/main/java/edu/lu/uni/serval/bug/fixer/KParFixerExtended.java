package edu.lu.uni.serval.bug.fixer;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.Calendar;

import edu.lu.uni.serval.json.MethodInfoUtils;
import edu.lu.uni.serval.json.PatchesLogs;
import edu.lu.uni.serval.json.util.PatchSpaceUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import edu.lu.uni.serval.config.Configuration;
import edu.lu.uni.serval.jdt.tree.ITree;
import edu.lu.uni.serval.par.templates.FixTemplate;
import edu.lu.uni.serval.par.templates.fix.ClassCastChecker;
import edu.lu.uni.serval.par.templates.fix.CollectionSizeChecker;
import edu.lu.uni.serval.par.templates.fix.ExpressionAdder;
import edu.lu.uni.serval.par.templates.fix.ExpressionRemover;
import edu.lu.uni.serval.par.templates.fix.ExpressionReplacer;
import edu.lu.uni.serval.par.templates.fix.MethodReplacer;
import edu.lu.uni.serval.par.templates.fix.NullPointerChecker;
import edu.lu.uni.serval.par.templates.fix.ParameterAdder;
import edu.lu.uni.serval.par.templates.fix.ParameterRemover;
import edu.lu.uni.serval.par.templates.fix.ParameterReplacer;
import edu.lu.uni.serval.par.templates.fix.RangeChecker;
import edu.lu.uni.serval.utils.Checker;
import edu.lu.uni.serval.utils.FileHelper;
import edu.lu.uni.serval.utils.SuspiciousPosition;

/**
 * Automated Program Repair Tool: kPAR.
 *
 * All fix templates are introduced in paper "Automatic patch generation learned from human-written patches".
 * https://dl.acm.org/citation.cfm?id=2486893
 *
 * @author kui.liu
 *
 */
public class KParFixerExtended extends AbstractFixer {

    private static Logger log = LoggerFactory.getLogger(KParFixerExtended.class);
    private final PatchesLogs jsonLogs = new PatchesLogs();
    private int totalPatches = 0;
    private final ArrayList<String> failedMethods = new ArrayList<>();

    public KParFixerExtended(String path, String projectName, int bugId, String defects4jPath) {
        super(path, projectName, bugId, defects4jPath);
        this.jsonLogs.setProjectName(projectName + "_" + bugId);
    }

    public KParFixerExtended(String path, String metric, String projectName, int bugId, String defects4jPath) {
        super(path, metric, projectName, bugId, defects4jPath);
        this.jsonLogs.setProjectName(projectName + "_" + bugId);
    }

    @Override
    public void fixProcess() {
        // Read paths of the buggy project.
        if (!dp.validPaths) return;

        // Read suspicious positions.
        List<SuspiciousPosition> suspiciousCodeList = readSuspiciousCodeFromFile(metric, buggyProject, dp);
        if (suspiciousCodeList == null) return;
        readPassingAndFailingTests();

        List<SuspCodeNode> triedSuspNode = new ArrayList<>();
        log.info("=======kPARFixer: Start to fix suspicious code======");
        for (SuspiciousPosition suspiciousCode : suspiciousCodeList) {
            SuspCodeNode scn = parseSuspiciousCode(suspiciousCode);
            if (scn == null) continue;
            // Json logs
            this.jsonLogs.addPriority(suspiciousCode.classPath, suspiciousCode.lineNumber, suspiciousCode.score);
            scn.score = suspiciousCode.score;

//			log.debug(scn.suspCodeStr);
            if (triedSuspNode.contains(scn)) continue;
            triedSuspNode.add(scn);
            // Match fix templates for this suspicious code with its context information.
            long startTime=Calendar.getInstance().getTimeInMillis();
            fixWithMatchedFixTemplates(scn);
            log.info("Generation time: "+Long.toString(Calendar.getInstance().getTimeInMillis()-startTime));
        }
        log.info("=======kPARFixer: Finish off fixing======");
        // Json logs
        createJsonLogs();
        log.debug("Not function level for JSON:");
        for (String fail: failedMethods) {
            System.out.println(fail);
        }
        log.info("totally created " + totalPatches + " patches");
    }

    protected void fixWithMatchedFixTemplates(SuspCodeNode scn) {

        // Parse context information of the suspicious code.
        List<Integer> contextInfoList = readAllNodeTypes(scn.suspCodeAstNode);
        List<Integer> distinctContextInfo = new ArrayList<>();
        for (Integer contInfo : contextInfoList) {
            if (!distinctContextInfo.contains(contInfo)) {
                distinctContextInfo.add(contInfo);
            }
        }
//		List<Integer> distinctContextInfo = contextInfoList.stream().distinct().collect(Collectors.toList());

        // generate patches with fix templates.
        FixTemplate ft = null;
        for (int contextInfo : distinctContextInfo) {
            if (Checker.isCastExpression(contextInfo)) {
                ft = new ClassCastChecker();
            } else if (Checker.isMethodInvocation(contextInfo) || Checker.isConstructorInvocation(contextInfo)
                    || Checker.isSuperConstructorInvocation(contextInfo) || Checker.isSuperMethodInvocation(contextInfo)
                    || Checker.isClassInstanceCreation(contextInfo)) {
//				// CollectionSizeChecker: method name must be "get".
                ft = new CollectionSizeChecker();
                generatePatches(ft, scn);

                ft = new ParameterAdder();
                generatePatches(ft, scn);

                ft = new ParameterRemover();
                generatePatches(ft, scn);

                ft = new ParameterReplacer();
                generatePatches(ft, scn);

                ft = new MethodReplacer();
            } else if (Checker.isIfStatement(contextInfo) || Checker.isWhileStatement(contextInfo) || Checker.isDoStatement(contextInfo)
                    || (Checker.isReturnStatement(contextInfo) && isBooleanReturnMethod(scn.suspCodeAstNode))) {
                ft = new ExpressionReplacer();
                generatePatches(ft, scn);

                ft = new ExpressionRemover();
                generatePatches(ft, scn);

                ft = new ExpressionAdder();
            } else if (!Checker.withBlockStatement(scn.suspCodeAstNode.getType()) && Checker.isConditionalExpression(contextInfo)) {
                // TODO
            } else if (Checker.isSimpleName(contextInfo)) {
                ft = new NullPointerChecker();
//				generatePatches(ft, scn);
//				if (this.minErrorTest == 0) break;
//
//				if (!distinctContextInfo.contains(25)) {// Do not re-initialize the variable(s) in IfStatement.
//					ft = new ObjectInitializer();
//				}
            } else if (Checker.isArrayAccess(contextInfo)) {
                ft = new RangeChecker();
//			} else if (Checker.isReturnStatement(contextInfo)) {
                // exchange true with false. TODO
            }
            if (ft == null) continue;
            generatePatches(ft, scn);
            ft = null;
        }
    }

    private boolean isBooleanReturnMethod(ITree suspCodeAstNode) {
        ITree parent = suspCodeAstNode.getParent();
        while (true) {
            if (parent == null) return false;
            if (Checker.isMethodDeclaration(parent.getType())) {
                break;
            }
            parent = parent.getParent();
        }

        String label = parent.getLabel();
        int indexOfMethodName = label.indexOf("MethodName:");

        // Read return type.
        String returnType = label.substring(label.indexOf("@@") + 2, indexOfMethodName - 2);
        int index = returnType.indexOf("@@tp:");
        if (index > 0) returnType = returnType.substring(0, index - 2);

        if ("boolean".equalsIgnoreCase(returnType))
            return true;

        return false;
    }

    private void generatePatches(FixTemplate ft, SuspCodeNode scn) {
        ft.setSuspiciousCodeStr(scn.suspCodeStr);
        ft.setSuspiciousCodeTree(scn.suspCodeAstNode);
        if (scn.javaBackup == null) ft.setSourceCodePath(dp.srcPath);
        else ft.setSourceCodePath(dp.srcPath, scn.javaBackup);
        ft.generatePatches();
        List<Patch> patchCandidates = ft.getPatches();

        // Test generated patches.
        if (patchCandidates.isEmpty()) return;
        saveGeneratedPatches(patchCandidates, scn, ft.getClass().getSimpleName());
    }

    private void saveGeneratedPatches(List<Patch> patches, SuspCodeNode scn, String fixname) {
        for (Patch patch: patches) {
            patch.buggyFileName = scn.suspiciousJavaFile;
            totalPatches++;

            String patchLocation = null;
            try {
                patchLocation = savePatch(scn, patch, fixname);
                if (patchLocation != null) {
                    String pathPrefix = Configuration.OUTPUT_DIR;
                    if (pathPrefix == null) {
                        pathPrefix = Configuration.TEMP_PATCHES_FILES_PATH;
                    }
                    patchLocation = patchLocation.substring((pathPrefix + this.buggyProject).length());
                }
            } catch (IllegalArgumentException e) {
                e.printStackTrace();
            }
            if (patchLocation == null) {
                log.error("SKIPPING the patch " + fixname + " " + totalPatches);
                totalPatches--;
                // rollbackFiles(scn);
                continue;
            }

            // Json logs
            int startPosition = patch.getBuggyCodeStartPos();
            int endPosition = patch.getBuggyCodeEndPos();
            String javafile = scn.targetJavaFile.getAbsolutePath();
            int startLine = PatchSpaceUtils.getLineNumberOnPosition(javafile, startPosition);
            int endLine = PatchSpaceUtils.getLineNumberOnPosition(javafile, endPosition);
            addLineJsonLogs(scn, fixname, patchLocation, startLine, endLine, startPosition, endPosition);
            addMutationRank(patchLocation, totalPatches);
        }
    }

    private String savePatch(SuspCodeNode scn, Patch patch, String fixname) throws IllegalArgumentException {
        String fixedCodeStr1 = patch.getFixedCodeStr1();
        String fixedCodeStr2 = patch.getFixedCodeStr2();
        int exactBuggyCodeStartPos = patch.getBuggyCodeStartPos();
        int exactBuggyCodeEndPos = patch.getBuggyCodeEndPos();
        String patchCode = fixedCodeStr1;
        boolean needBuggyCode = false;
        if (exactBuggyCodeEndPos > exactBuggyCodeStartPos) {
            needBuggyCode = true;
            if (exactBuggyCodeStartPos < 0 ) {
                exactBuggyCodeStartPos = scn.startPos;
                exactBuggyCodeEndPos = scn.endPos;
            }
        } else if (exactBuggyCodeStartPos == -1 && exactBuggyCodeEndPos == -1) {
            exactBuggyCodeStartPos = scn.startPos;
            exactBuggyCodeEndPos = scn.endPos;
        } else if (exactBuggyCodeStartPos == exactBuggyCodeEndPos) {
            exactBuggyCodeStartPos = scn.startPos;
        }
        String javaCode = FileHelper.readFile(scn.javaBackup);
        String buggyCode;
        File newFile = null;
        patch.setBuggyCodeStartPos(exactBuggyCodeStartPos);
        patch.setBuggyCodeEndPos(exactBuggyCodeEndPos);
        try {
            buggyCode = javaCode.substring(exactBuggyCodeStartPos, exactBuggyCodeEndPos);
            if (needBuggyCode) {
                patchCode += buggyCode;
                if (fixedCodeStr2 != null) {
                    patchCode += fixedCodeStr2;
                }
            }

            String pathPrefix = Configuration.OUTPUT_DIR;
            if (pathPrefix == null) {
                pathPrefix = Configuration.TEMP_PATCHES_FILES_PATH;
            }

            newFile = new File(pathPrefix + this.buggyProject + "/" + this.totalPatches + "_" + fixname + "/" + scn.targetJavaFile.getName());
            String patchedJavaFile = javaCode.substring(0, exactBuggyCodeStartPos) + patchCode + javaCode.substring(exactBuggyCodeEndPos);
            FileHelper.outputToFile(newFile, patchedJavaFile, false);
        } catch (StringIndexOutOfBoundsException e) {
            log.debug(exactBuggyCodeStartPos + " ==> " + exactBuggyCodeEndPos + " : " + javaCode.length());
            e.printStackTrace();
            buggyCode = "===StringIndexOutOfBoundsException===";
        }

        patch.setBuggyCodeStr(buggyCode);
        patch.setFixedCodeStr1(patchCode);

        if (newFile == null) return null;
        return newFile.getAbsolutePath();
    }

    private List<Integer> readAllNodeTypes(ITree suspCodeAstNode) {
        List<Integer> nodeTypes = new ArrayList<>();
        nodeTypes.add(suspCodeAstNode.getType());
        List<ITree> children = suspCodeAstNode.getChildren();
        for (ITree child : children) {
            if (Checker.isStatement(child.getType())) break;
            nodeTypes.addAll(readAllNodeTypes(child));
        }
        return nodeTypes;
    }

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
            } else {
                try {
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
                } catch (Exception e) {
                    System.out.println(test);
                }
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
                log.info("Couldn't create json logs ;(, changing existing logs file " + logs.getAbsolutePath());
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
            System.out.println(scn.targetJavaFile.getAbsolutePath());
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

}
