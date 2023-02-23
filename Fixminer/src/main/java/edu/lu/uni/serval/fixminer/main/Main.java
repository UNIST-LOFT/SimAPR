package edu.lu.uni.serval.fixminer.main;

import java.io.File;
import java.util.List;

import edu.lu.uni.serval.bug.fixer.FixMinerFixer;
import edu.lu.uni.serval.config.Configuration;
import edu.lu.uni.serval.fixminer.LiteralReader;
import edu.lu.uni.serval.fixminer.ProjectLiteral;
import picocli.CommandLine;
import picocli.CommandLine.Option;
import picocli.CommandLine.Parameters;

public class Main {
	@Option(names={"-l","--max-loc"},description = "Top n location from FL")
	private int maxLoc=0;
	@Option(names={"--sub-template"},description = "Generate sub-template patches")
	private boolean subTemplate=false;

	@Parameters(index="0")
	String failedTestFilePath;
	@Parameters(index="1")
	String suspCodeFilePath;
	@Parameters(index="2")
	String buggyProjectPath;
	@Parameters(index="3")
	String d4jPath;
	@Parameters(index="4")
	String projectName;

	public static void main(String[] args) {
		Main main = new Main();
		new CommandLine(main).parseArgs(args);
		if (main.failedTestFilePath==null || main.suspCodeFilePath==null || main.buggyProjectPath==null || main.d4jPath==null || main.projectName==null) {
			System.out.println("Arguments: <Failed_Test_Cases_File_Path> <Suspicious_Code_Positions_File_Path> <Buggy_Project_Path> <defects4j_Path> <Project_Name>");
			System.exit(0);
		}

		if (main.maxLoc!=0) System.out.println("Use top "+Integer.toString(main.maxLoc)+" locations.");
		Configuration.failedTestCasesFilePath = main.failedTestFilePath; // failedTestCases/
		Configuration.suspPositionsFilePath = main.suspCodeFilePath;   // BugPositions/
		String buggyProjectsPath = main.buggyProjectPath;// "../Defects4JData/"
		String defects4jPath = main.d4jPath; // "../defects4j/"
		String projectName = main.projectName; // "Chart_1"
		Configuration.faultLocalizationMetric = "Ochiai";
		System.out.println(projectName);
		fixBug(buggyProjectsPath, defects4jPath, projectName,main.maxLoc,main.subTemplate);
	}

	private static void fixBug(String buggyProjectsPath, String defects4jPath, String buggyProjectName,int maxLocation,boolean useSubTemplate) {
		String suspiciousFileStr = Configuration.suspPositionsFilePath;
		
		String dataType = "FixMiner";
		String[] elements = buggyProjectName.split("_");
		String projectName = elements[0];
		int bugId;
		try {
			bugId = Integer.valueOf(elements[1]);
		} catch (NumberFormatException e) {
			System.err.println("Please input correct buggy project ID, such as \"Chart_1\".");
			return;
		}
		
		List<ProjectLiteral> literals = LiteralReader.read(buggyProjectName);
		
		FixMinerFixer fixer = new FixMinerFixer(buggyProjectsPath, projectName, bugId, defects4jPath);
		fixer.metric = Configuration.faultLocalizationMetric;
		fixer.dataType = dataType;
		fixer.literals = literals; // some local data. FIXME: might be useless.
		fixer.useSubTemplate = useSubTemplate;
		fixer.suspCodePosFile = new File(suspiciousFileStr);
		if (fixer.minErrorTest == Integer.MAX_VALUE) {
			System.out.println("Failed to defects4j compile bug " + buggyProjectName);
			return;
		}
		
		fixer.fixProcess(maxLocation);
		
		int fixedStatus = fixer.fixedStatus;
		System.out.println("Finish generating patch candidates "+buggyProjectName);
	}

}
