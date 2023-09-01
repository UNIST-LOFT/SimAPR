package edu.lu.uni.serval.bug.fixer;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.Calendar;

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
import edu.lu.uni.serval.utils.PathUtils;
import edu.lu.uni.serval.utils.SuspiciousPosition;
import kr.ac.unist.apr.MethodFinder;

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
    private int totalPatches = 0;
    private final ArrayList<String> failedMethods = new ArrayList<>();

    public KParFixerExtended(String path, String projectName, int bugId, String defects4jPath) {
        super(path, projectName, bugId, defects4jPath);
    }

    public KParFixerExtended(String path, String metric, String projectName, int bugId, String defects4jPath) {
        super(path, metric, projectName, bugId, defects4jPath);
    }

    @Override
    public void fixProcess() {
        // Read paths of the buggy project.
        if (!dp.validPaths) return;

        MethodFinder.parseFiles(fullBuggyProjectPath+PathUtils.getSrcPath(buggyProject).get(2),buggyProject);
        // Read suspicious positions.
        List<SuspiciousPosition> suspiciousCodeList = readSuspiciousCodeFromFile(metric, buggyProject, dp);
        if (suspiciousCodeList == null) return;
        readPassingAndFailingTests();

        List<SuspCodeNode> triedSuspNode = new ArrayList<>();
        log.info("=======kPARFixer: Start to fix suspicious code======");
        for (SuspiciousPosition suspiciousCode : suspiciousCodeList) {
            SuspCodeNode scn = parseSuspiciousCode(suspiciousCode);
            if (scn == null) continue;

//			log.debug(scn.suspCodeStr);
            if (triedSuspNode.contains(scn)) continue;
            triedSuspNode.add(scn);
            // Match fix templates for this suspicious code with its context information.
            long startTime=Calendar.getInstance().getTimeInMillis();
            fixWithMatchedFixTemplates(scn);
            log.info("Generation time: "+Long.toString(Calendar.getInstance().getTimeInMillis()-startTime));
        }
        log.info("=======kPARFixer: Finish off fixing======");
        jsonInfo.setSwitchInfos(switchInfos);
        jsonInfo.saveToFile(buggyProject);

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
        addPatchesToInfo(patchCandidates, scn);
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
        String[] allTests;
        try{
            allTests = FileHelper.readFile(fullBuggyProjectPath + "/" + "all-tests.txt").split("\n");
        } catch (NullPointerException e){
            allTests=FileHelper.readFile(fullBuggyProjectPath + "/" + "all_tests").split("\n");
        }
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

    }
}
