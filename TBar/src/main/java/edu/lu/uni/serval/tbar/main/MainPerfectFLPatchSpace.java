package edu.lu.uni.serval.tbar.main;

import edu.lu.uni.serval.tbar.TBarFixerPatchSpace;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import edu.lu.uni.serval.tbar.TBarFixer;
import edu.lu.uni.serval.tbar.TBarFixer.Granularity;
import edu.lu.uni.serval.tbar.config.Configuration;
import sun.security.krb5.Config;

import java.io.File;

/**
 * Fix bugs with the known bug positions.
 *
 * @author kui.liu
 *
 */
public class MainPerfectFLPatchSpace {

    private static Logger log = LoggerFactory.getLogger(MainPerfectFLPatchSpace.class);
    private static Granularity granularity = Granularity.File;

    public static void main(String[] args) {
        String bugDataPath = args[0];//"/Users/kui.liu/Public/Defects4J_Data/";//
        String bugId = args[1]; //"Closure_4";//
        String defects4jHome = args[2];//"/Users/kui.liu/Public/GitRepos/defects4j/";//
        if (args.length > 3) {
            Configuration.OUTPUT_DIR = args[3];
        }
        Configuration.WORK_DIR = bugDataPath + bugId + "/";
//        Configuration.failedTestCasesFilePath = args[3];//"/Users/kui.liu/eclipse-fault-localization/FL-VS-APR/data/FailedTestCases/";//
//        Configuration.knownBugPositions = args[4];
        boolean isTestFixPatterns = false;//Boolean.valueOf(args[3]);//
//        String granularityStr = "Line";
        // System.out.println(bugId);
//        if ("line".equalsIgnoreCase(granularityStr) || "l".equalsIgnoreCase(granularityStr)) {
//            granularity = Granularity.Line;
//            if (isTestFixPatterns) Configuration.outputPath += "FixPatterns/";
//            else Configuration.outputPath += "PerfectFL/";
//        }
        fixBug(bugDataPath, defects4jHome, bugId, isTestFixPatterns);
    }

    public static void fixBug(String bugDataPath, String defects4jHome, String bugIdStr, boolean isTestFixPatterns) {
        Configuration.outputPath += "NormalFL/";
        String suspiciousFileStr = Configuration.suspPositionsFilePath;

        String[] elements = bugIdStr.split("_");
        String projectName = elements[0];
        int bugId;
        try {
            bugId = Integer.valueOf(elements[1]);
        } catch (NumberFormatException e) {
            System.err.println("Please input correct buggy project ID, such as \"Chart_1\".");
            return;
        }

        TBarFixer fixer = new TBarFixerPatchSpace(bugDataPath, projectName, bugId, defects4jHome);
        fixer.dataType = "TBar";
        fixer.metric = Configuration.faultLocalizationMetric;
        fixer.suspCodePosFile = new File(suspiciousFileStr);
        if (Integer.MAX_VALUE == fixer.minErrorTest) {
            System.out.println("Failed to defects4j compile bug " + bugIdStr);
            return;
        }

        fixer.fixProcess();
    }

}
