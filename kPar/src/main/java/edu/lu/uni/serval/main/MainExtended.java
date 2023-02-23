package edu.lu.uni.serval.main;

import edu.lu.uni.serval.bug.fixer.AbstractFixer;
import edu.lu.uni.serval.bug.fixer.KParFixerExtended;
import edu.lu.uni.serval.config.Configuration;

import java.io.File;

public class MainExtended {

    public static void main(String[] args) {
        String buggyProjectsPath = args[0];// "../Defects4JData/"
        String projectName = args[1]; // "Chart_1"
        String defects4jPath = args[2]; // "../defects4j/"
        if (args.length > 3) {
            System.out.println(args[3]);
            Configuration.OUTPUT_DIR = args[3];
        }
        Configuration.WORK_DIR = buggyProjectsPath + projectName + "/";
        System.out.println(projectName);
        fixBug(buggyProjectsPath, defects4jPath, projectName);
    }

    public static void fixBug(String buggyProjectsPath, String defects4jPath, String buggyProjectName) {
        String suspiciousFileStr = Configuration.suspPositionsFilePath;

        String dataType = "kPAR";
        String[] elements = buggyProjectName.split("_");
        String projectName = elements[0];
        int bugId;
        try {
            bugId = Integer.valueOf(elements[1]);
        } catch (NumberFormatException e) {
            System.err.println("Please input correct buggy project ID, such as \"Chart_1\".");
            return;
        }

        AbstractFixer fixer = new KParFixerExtended(buggyProjectsPath, projectName, bugId, defects4jPath);
        fixer.metric = Configuration.faultLocalizationMetric;
        fixer.dataType = dataType;
        fixer.suspCodePosFile = new File(suspiciousFileStr);
        if (Integer.MAX_VALUE == fixer.minErrorTest) {
            System.out.println("Failed to defects4j compile bug " + buggyProjectName);
            return;
        }

        fixer.fixProcess();
    }

}
