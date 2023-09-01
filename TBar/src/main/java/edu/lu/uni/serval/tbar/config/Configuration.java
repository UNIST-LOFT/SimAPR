package edu.lu.uni.serval.tbar.config;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import edu.lu.uni.serval.tbar.TBarTransformerFixer;
import edu.lu.uni.serval.tbar.fixtemplate.FixTemplate;

public class Configuration {

	public static String knownBugPositions = "BugPositions.txt";
	public static String suspPositionsFilePath = "SuspiciousCodePositions_updated/"; // SuspiciousCodePositions/
	public static String failedTestCasesFilePath = "FailedTestCases/";
	public static String faultLocalizationMetric = "Ochiai";
	public static String outputPath = "OUTPUT/";

	public static String TEMP_FILES_PATH = "temp/Original/";
	public static String TEMP_PATCHES_FILES_PATH = "temp/Patches/";
	public static final long SHELL_RUN_TIMEOUT = 300L;
	public static final long TEST_SHELL_RUN_TIMEOUT = 600L;

	public static List<FixTemplate> fixTemplates = new ArrayList<>();
	public static final String JSON_LOG_PATH = "switch-info.json";

	public static String OUTPUT_DIR = null;
	public static String WORK_DIR = null;
	public static String cacheFile="/root/project/experiment/.cache-tbar/";
}
