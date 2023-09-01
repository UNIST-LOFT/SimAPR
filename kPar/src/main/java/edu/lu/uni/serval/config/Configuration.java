package edu.lu.uni.serval.config;

/**
 * Configuration of PAR.
 * 
 * @author kui.liu
 *
 */
public class Configuration {

	public static String knownBugPositions = "BugPositions.txt";
	public static String suspPositionsFilePath = "SuspiciousCodePositions/";
	public static String failedTestCasesFilePath = "FailedTestCases/";
	public static String faultLocalizationMetric = "Ochiai";
	public static String outputPath = "OUTPUT/";
	public static final long SHELL_RUN_TIMEOUT = 10800L;

	public static String OUTPUT_DIR = null;
	public static String WORK_DIR = null;
	public static String TEMP_FILES_PATH = "/tmp/";
	public static String TEMP_PATCHES_FILES_PATH = "/tmp/Patches/";
	public static final String JSON_LOG_PATH = "switch-info.json";
	public static String cacheFile="/root/project/experiment/.cache-kpar/";
}
