package edu.lu.uni.serval.tbar.main;

import java.util.ArrayList;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import edu.lu.uni.serval.tbar.TBarTransformerFixer;
import edu.lu.uni.serval.tbar.config.Configuration;
import edu.lu.uni.serval.tbar.fixpatterns.*;
import edu.lu.uni.serval.tbar.fixtemplate.FixTemplate;

public class MainTransformerCheck {

    private static Logger log = LoggerFactory.getLogger(MainTransformerCheck.class);

    public static void main(String[] args) {
        String bugFileLocation = args[0]; // src/com/google/javascript/jscomp/TypeCheck.java
        int bugLine = Integer.parseInt(args[1]); // 25
        String projectPath = args[2]; // D4J/projects
        String projectName = args[3]; // test
        String transformers = args[4]; // NullPointer;MethodChanger

        log.info(bugFileLocation);
        log.info("Transformers: " + transformers);

        createTransformers(transformers.split("-"));
        Configuration.outputPath = "TransformerCheck/";

        fixBug(bugFileLocation, bugLine, projectPath, projectName);
    }

    private static void fixBug(String bugFileLocation, int bugLine, String projectPath, String projectName) {
        TBarTransformerFixer fixer = new TBarTransformerFixer(
            bugFileLocation, bugLine, projectPath, projectName
        );
        fixer.fixProcess();
    }

    private static void createTransformers(String[] transformerNames) {
        ArrayList<FixTemplate> templates = new ArrayList<>();
        for (String name: transformerNames) {
            FixTemplate ft = null;
            switch(name) {
                case "ClassCastChecker":
                    ft = new ClassCastChecker();
                    break;
                case "DataTypeReplacer":
                    ft = new DataTypeReplacer();
                    break;
                case "MethodInvocationMutator":
                    ft = new MethodInvocationMutator();
                    break;
                case "OperatorMutator(0)":
                    ft = new OperatorMutator(0);
                    break;
                case "OperatorMutator(2)":
                    ft = new OperatorMutator(2);
                    break;
                case "OperatorMutator(4)":
                    ft = new OperatorMutator(4);
                    break;
                case "ConditionalExpressionMutator(0)":
                    ft = new ConditionalExpressionMutator(0);
                    break;
                case "ConditionalExpressionMutator(1)":
                    ft = new ConditionalExpressionMutator(1);
                    break;
                case "ConditionalExpressionMutator(2)":
                    ft = new ConditionalExpressionMutator(2);
                    break;
                case "ICASTIdivCastToDouble":
                    ft = new ICASTIdivCastToDouble();
                    break;
                case "LiteralExpressionMutator":
                    ft = new LiteralExpressionMutator();
                    break;
                case "NPEqualsShouldHandleNullArgument":
                    ft = new NPEqualsShouldHandleNullArgument();
                    break;
                case "RangeChecker(false)":
                    ft = new RangeChecker(false);
                    break;
                case "RangeChecker(true)":
                    ft = new RangeChecker(true);
                    break;
                case "ReturnStatementMutator":
                    ft = new ReturnStatementMutator("String");
                    break;
                case "VariableReplacer":
                    ft = new VariableReplacer();
                    break;
                case "StatementMover":
                    ft = new StatementMover();
                    break;
                case "StatementRemover":
                    ft = new StatementRemover();
                    break;
                case "StatementInserter":
                    ft = new StatementInserter();
                    break;
                case "NullPointerChecker":
                    ft = new NullPointerChecker();
                    break;
            }
            if (ft == null) continue;
            templates.add(ft);
        }
        Configuration.fixTemplates = templates;
    }

}