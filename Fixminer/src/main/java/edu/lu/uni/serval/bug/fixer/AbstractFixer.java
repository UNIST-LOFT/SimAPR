package edu.lu.uni.serval.bug.fixer;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.lang.reflect.Array;
import java.nio.file.CopyOption;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Calendar;

import org.apache.commons.lang3.math.NumberUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import anonymous.CacheInfo;
import anonymous.JsonInfo;
import anonymous.SwitchInfo;
import anonymous.TestValidator;
import anonymous.MethodLineFinder.FunctionLocation;
import anonymous.SwitchInfo.FileInfo;
import anonymous.SwitchInfo.LineInfo;
import edu.lu.uni.serval.config.Configuration;
import edu.lu.uni.serval.dataprepare.DataPreparer;
import edu.lu.uni.serval.jdt.tree.ITree;
import edu.lu.uni.serval.patch.Patch;
import edu.lu.uni.serval.utils.FileHelper;
import edu.lu.uni.serval.utils.FileUtils;
import edu.lu.uni.serval.utils.PathUtils;
import edu.lu.uni.serval.utils.ShellUtils;
import edu.lu.uni.serval.utils.SuspiciousCodeParser;
import edu.lu.uni.serval.utils.SuspiciousPosition;
import edu.lu.uni.serval.utils.TestUtils;

/**
 * Abstract Fixer.
 * 
 * @author kui.liu
 *
 */
public abstract class AbstractFixer implements IFixer {

	public static String removeInnerClassFromSourcePath(String sourcePath) {
		String result=sourcePath;
		if (sourcePath.contains("$")){
			int index=sourcePath.indexOf('$');
			int extIndex=sourcePath.lastIndexOf('.');
			result=sourcePath.substring(0, index)+sourcePath.substring(extIndex);
		}
		return result;
	}
	
	private static Logger log = LoggerFactory.getLogger(AbstractFixer.class);
	
	public String metric = "null";          // Fault localization metric.
	protected String path = "";
	protected String buggyProject = "";     // The buggy project name.
	protected String defects4jPath;         // The path of local installed defects4j.
	public int minErrorTest;                // Number of failed test cases before fixing.
	protected int minErrorTestAfterFix = 0; // Number of failed test cases after fixing
	protected String fullBuggyProjectPath;  // The full path of the local buggy project.
	public String outputPath = "";          // Output path for the generated patches.
	public File suspCodePosFile = null;     // The file containing suspicious code positions localized by FL tools.
	protected DataPreparer dp;              // The needed data of buggy program for compiling and testing.

	private String failedTestCaseClasses = ""; // Classes of the failed test cases before fixing.
	// All specific failed test cases after testing the buggy project with defects4j command in Java code before fixing.
	protected List<String> failedTestStrList = new ArrayList<>();
	// All specific failed test cases after testing the buggy project with defects4j command in terminal before fixing.
	protected List<String> failedTestCasesStrList = new ArrayList<>();
	// The failed test cases after running defects4j command in Java code but not in terminal.
	private List<String> fakeFailedTestCasesList = new ArrayList<>();
	
	// 0: failed to fix the bug, 1: succeeded to fix the bug. 2: partially succeeded to fix the bug.
	public int fixedStatus = 0;
	public String dataType = "";
	protected int patchId = 0;
//	private TimeLine timeLine;

	// Information json of all generated patches
	protected JsonInfo jsonInfo;
	// Patch space tree
	protected List<FileInfo> switchInfos=new ArrayList<>();
	// Method lists
	protected Map<String, List<FunctionLocation>> methodLists = new HashMap<>();
	public boolean useSubTemplate = false;

	protected boolean isSecondLoop=false;
	protected List<String> actualFailedTests;
	protected List<String> actualPassedTests;
	protected List<String> failedPassingTests;
	protected List<JsonInfo.Location> flList=new ArrayList<>();
	protected String cachePath;
	protected CacheInfo cacheInfo=new CacheInfo();

	
	public AbstractFixer(String path, String projectName, int bugId, String defects4jPath) {
		this.path = path;
		this.buggyProject = projectName + "_" + bugId;
		fullBuggyProjectPath = path + buggyProject;
		this.defects4jPath = defects4jPath;
		this.cachePath=Configuration.cacheFile+"/"+buggyProject+"-cache.json";

		this.jsonInfo=new JsonInfo(buggyProject);

		// // Save original source file to temp dir
		// File tempDir=new File(fullBuggyProjectPath+"/temp");
		// if(!tempDir.exists()) tempDir.mkdir();
		// tempDir=new File(fullBuggyProjectPath+"/temp/Original");
		// if(!tempDir.exists()) tempDir.mkdir();
		// tempDir=new File(fullBuggyProjectPath+"/temp/Original/TBar");
		// if(!tempDir.exists()) tempDir.mkdir();
		// tempDir=new File(fullBuggyProjectPath+"/temp/Original/TBar/"+buggyProject);
		// if(!tempDir.exists()) tempDir.mkdir();

		// try {
		// 	JsonInfo.copyOriginal(fullBuggyProjectPath+"/src/main/java", fullBuggyProjectPath+"/temp/Original/TBar/"+buggyProject);
		// } catch (Exception e1) {
		// 	log.error("Copy original file failed!");
		// 	e1.printStackTrace();
		// }
		TestUtils.compileProjectWithDefects4j(path + buggyProject,defects4jPath);
		minErrorTest = TestUtils.getFailTestNumInProject(path + buggyProject, defects4jPath, failedTestStrList);
		log.info(buggyProject + " Failed Tests: " + this.minErrorTest);
		
		// Read paths of the buggy project.
		this.dp = new DataPreparer(path);
		dp.prepareData(buggyProject);

		readPreviouslyFailedTestCases();

		actualFailedTests=failedTestCasesStrList;
		actualPassedTests=new ArrayList<>(Arrays.asList(dp.testCases));
		failedPassingTests=new ArrayList<>();
		TestValidator testValid=new TestValidator(path,buggyProject,defects4jPath);
		try {
			testValid.checkoutBuggyVersion();
			List<String> failedPassTests=testValid.getFailedPassTests();
			for(String failedTest:failedPassTests){
				if (actualFailedTests.contains(failedTest)) {
					int index=actualFailedTests.indexOf(failedTest);
					actualFailedTests.remove(index);
					log.info("Remove "+failedTest+" from fail test");
				}

				failedPassingTests.add(failedTest);
			}
		} catch (IOException e) {
			log.error("Error on get failed tests:");
			e.printStackTrace();
		}
		jsonInfo.setTestList(actualFailedTests, actualPassedTests);
		jsonInfo.setFailedPassTest(failedPassingTests);
	}

	public AbstractFixer(String path, String metric, String projectName, int bugId, String defects4jPath) {
		this(path, projectName, bugId, defects4jPath);
		this.metric = metric;
	}
	
	private void readPreviouslyFailedTestCases() {
		String[] failedTestCases = FileHelper.readFile(Configuration.failedTestCasesFilePath + this.buggyProject + ".txt").split("\n");
		List<String> failedTestCasesList = new ArrayList<>();
		List<String> failed = new ArrayList<>();
		for (int index = 1, length = failedTestCases.length; index < length; index ++) {
			// - org.jfree.data.general.junit.DatasetUtilitiesTests::testBug2849731_2
			String failedTestCase = failedTestCases[index].trim();
			failed.add(failedTestCase);
			failedTestCase = failedTestCase.substring(failedTestCase.indexOf("-") + 1).trim();
			failedTestCasesStrList.add(failedTestCase);
			int colonIndex = failedTestCase.indexOf("::");
			if (colonIndex > 0) {
				failedTestCase = failedTestCase.substring(0, colonIndex);
			}
			if (!failedTestCasesList.contains(failedTestCase)) {
				this.failedTestCaseClasses += failedTestCase + " ";
				failedTestCasesList.add(failedTestCase);
			}
		}
		
		List<String> tempFailed = new ArrayList<>();
		tempFailed.addAll(this.failedTestStrList);
		tempFailed.removeAll(failed);
		
		// We call them as fake failed-passing test cases.
		this.fakeFailedTestCasesList.addAll(tempFailed);
	}

	public List<SuspiciousPosition> readSuspiciousCodeFromFile(String metric, String path, String buggyProject, DataPreparer dp) {
		File suspiciousFile = null;
		File suspiciousFileBackup=null;
		if (this.suspCodePosFile == null) {
			suspiciousFileBackup = new File(Configuration.suspPositionsFilePath);
		} else {
			suspiciousFileBackup = this.suspCodePosFile;
		}

		suspiciousFile = new File(suspiciousFileBackup.getPath() + "/" + this.buggyProject + "/" + this.metric + ".txt");
		if (!suspiciousFile.exists()) suspiciousFile = new File(suspiciousFileBackup.getPath() + "/" + this.buggyProject + "/" + this.metric.toLowerCase() + ".txt");
		if (!suspiciousFile.exists()) suspiciousFile = new File(suspiciousFileBackup.getPath() + "/" + this.buggyProject + "/All.txt");
		if (!suspiciousFile.exists()) return null;
		List<SuspiciousPosition> suspiciousCodeList = new ArrayList<>();
		try {
			FileReader fileReader = new FileReader(suspiciousFile);
            BufferedReader reader = new BufferedReader(fileReader);
            String line = null;
			int rank=0;
            while ((line = reader.readLine()) != null) {
            	String[] elements = line.split("@");
            	SuspiciousPosition sp = new SuspiciousPosition();
            	sp.classPath = elements[0];
            	sp.lineNumber = Integer.valueOf(elements[1]);
				sp.score=Double.valueOf(elements[2]);
				sp.rank=rank++;
				JsonInfo.Location newLoc=new JsonInfo.Location(sp.classPath, sp.lineNumber, Double.valueOf(elements[2]));
				jsonInfo.addFaultLocation(newLoc);
				this.flList.add(newLoc);
            	suspiciousCodeList.add(sp);
            }
            reader.close();
            fileReader.close();
        }catch (Exception e){
        	e.printStackTrace();
        	log.debug("Reloading Localization Result...");
            return null;
        }
		if (suspiciousCodeList.isEmpty()) return null;
		return suspiciousCodeList;
	}
	
	@Override
	public SuspCodeNode parseSuspiciousCode(SuspiciousPosition suspiciousCode) {
		String suspiciousClassName = suspiciousCode.classPath;
		int buggyLine = suspiciousCode.lineNumber;
		
		log.debug(suspiciousClassName + " ===" + buggyLine);
		String suspiciousJavaFile = suspiciousClassName.replace(".", "/") + ".java";
		
		suspiciousClassName = suspiciousJavaFile.substring(0, suspiciousJavaFile.length() - 5).replace("/", ".");
		
		String filePath = dp.srcPath + suspiciousJavaFile;
		filePath=removeInnerClassFromSourcePath(filePath);
		SuspiciousCodeParser scp = new SuspiciousCodeParser();
		scp.parseSuspiciousCode(new File(filePath), buggyLine);
		
		ITree suspCodeAstNode = scp.getSuspiciousCodeAstNode();
		String suspCodeStr = scp.getSuspiciousCodeStr();
		if (suspCodeAstNode == null || suspCodeStr == null) {
			log.debug("Failed to identify the buggy statement in: " + suspiciousClassName + " --- " + buggyLine);
			return null;
		}
		log.info("Suspicious Code: \n" + suspCodeStr);
		
		int startPos = suspCodeAstNode.getPos();
		int endPos = startPos + suspCodeAstNode.getLength();
		
		File targetJavaFile = new File(removeInnerClassFromSourcePath(FileUtils.getFileAddressOfJava(dp.srcPath, suspiciousClassName)));
        File targetClassFile = new File(FileUtils.getFileAddressOfClass(dp.classPath, suspiciousClassName));
        File javaBackup = new File(FileUtils.tempJavaPath(suspiciousClassName,  this.dataType + "/" + this.buggyProject));
        File classBackup = new File(FileUtils.tempClassPath(suspiciousClassName, this.dataType + "/" + this.buggyProject));
        try {
        	if (javaBackup.exists()) javaBackup.delete();
        	if (classBackup.exists()) classBackup.delete();
			Files.copy(targetJavaFile.toPath(), javaBackup.toPath(),StandardCopyOption.REPLACE_EXISTING);
			Files.copy(targetClassFile.toPath(), classBackup.toPath(),StandardCopyOption.REPLACE_EXISTING);
		} catch (IOException e) {
			e.printStackTrace();
		}
        
        SuspCodeNode scn = new SuspCodeNode(javaBackup, classBackup, targetJavaFile, targetClassFile, 
        		startPos, endPos, suspCodeAstNode, suspCodeStr, suspiciousJavaFile, buggyLine,suspiciousCode.score,suspiciousCode.rank);
        return scn;
	}

	protected List<Patch> triedPatchCandidates = new ArrayList<>();	
	private Map<String,Integer> countOfLocationMutator=new HashMap<>();

	protected void addPatchesToInfo(List<Patch> patchCandidates,SuspCodeNode scn){
		log.debug("Add "+Integer.toString(patchCandidates.size())+ " patches: File: "+scn.suspiciousJavaFile+", Line: "+Integer.toString(scn.buggyLine));
		for (Patch patch : patchCandidates) {
			patch.buggyFileName = scn.suspiciousJavaFile;
			if (this.triedPatchCandidates.contains(patch)) {
				try {
					scn.targetJavaFile.delete();
					scn.targetClassFile.delete();
					Files.copy(scn.javaBackup.toPath(), scn.targetJavaFile.toPath(),StandardCopyOption.REPLACE_EXISTING);
					Files.copy(scn.classBackup.toPath(), scn.targetClassFile.toPath(),StandardCopyOption.REPLACE_EXISTING);
				} catch (IOException e) {
					e.printStackTrace();
				}
				continue;
			}
			patchId++;
			// this.triedPatchCandidates.add(patch);
			String mutatorName=patch.mutator.getSimpleName();

			// Save patched source file to temp dir
			String loopId=this.isSecondLoop? "1":"0";
			File tempDir=new File("d4j");
			if(!tempDir.exists()) tempDir.mkdir();
			tempDir=new File("d4j/"+buggyProject);
			if(!tempDir.exists()) tempDir.mkdir();
			tempDir=new File("d4j/"+buggyProject+"/"+loopId);
			if(!tempDir.exists()) tempDir.mkdir();
			tempDir=new File("d4j/"+buggyProject+"/"+loopId+"/"+Integer.toString(scn.rank));
			if(!tempDir.exists()) tempDir.mkdir();
			tempDir=new File("d4j/"+buggyProject+"/"+loopId+"/"+Integer.toString(scn.rank)+"/"+mutatorName);
			if(!tempDir.exists()) tempDir.mkdir();

			if (!countOfLocationMutator.containsKey(mutatorName)) countOfLocationMutator.put(mutatorName, 0);
			String fixedDir="d4j/"+buggyProject+"/"+loopId+"/"+Integer.toString(scn.rank)+"/"+
						mutatorName+"/"+Integer.toString(patchId)+"/";
			String fixedPath=fixedDir+scn.suspiciousJavaFile;
			tempDir=new File(fixedDir);
			if(!tempDir.exists()) tempDir.mkdir();

			String file=(PathUtils.getSrcPath(buggyProject).get(2)).substring(1)+scn.suspiciousJavaFile;
			file=removeInnerClassFromSourcePath(file);
			int line=scn.buggyLine;
			int startPos=scn.startPos;
			int endPos=scn.endPos;
			double score=scn.flScore;

			FileInfo fileInfo=null;
			for (FileInfo tempFileInfo:switchInfos){
				if (tempFileInfo.fileName.equals(file)){
					fileInfo=tempFileInfo;
					break;
				}
			}
			if (fileInfo==null){
				fileInfo=new FileInfo(file,(scn.targetClassFile.getPath().replaceFirst(fullBuggyProjectPath,"")).substring(1));
				log.debug(fileInfo.className);
				switchInfos.add(fileInfo);
			}

			LineInfo lineInfo=null;
			for (LineInfo tempLineInfo:fileInfo.lineInfos){
				if (tempLineInfo.line==line){
					lineInfo=tempLineInfo;
					break;
				}
			}
			if (lineInfo==null){
				lineInfo=new LineInfo(line);
				lineInfo.id=scn.rank;
				fileInfo.lineInfos.add(lineInfo);
			}

			List<String> dirs=Arrays.asList(fixedPath.split("/"));
			String sourceFile=dirs.get(dirs.size()-1);
			sourceFile=removeInnerClassFromSourcePath(sourceFile);

			SwitchInfo newInfo=new SwitchInfo();
			newInfo.startOffset=startPos;
			newInfo.endOffset=endPos;
			newInfo.fixedSourcePath=loopId+"/"+Integer.toString(scn.rank)+"/"+
							mutatorName+"/"+Integer.toString(patchId)+"/"+sourceFile;
			newInfo.score=score;
			newInfo.mutator=patch.mutator;
			newInfo.id=patchId;
			patch.id=patchId;
			lineInfo.switchInfos.add(newInfo);

			tempDir=new File(fixedDir);
			if(!tempDir.exists()) tempDir.mkdir();

			addPatchCodeToFile(scn, patch, fixedDir+sourceFile);
			jsonInfo.addPatchRanking(newInfo.fixedSourcePath);
		}
	}
	
	protected void testGeneratedPatches(List<Patch> patchCandidates, SuspCodeNode scn) {
		// Testing generated patches.
		for (Patch patch : patchCandidates) {
			patch.buggyFileName = scn.suspiciousJavaFile;
			addPatchCodeToFile(scn, patch);// Insert the patch.
			if (this.triedPatchCandidates.contains(patch)) {
				try {
					scn.targetJavaFile.delete();
					scn.targetClassFile.delete();
					Files.copy(scn.javaBackup.toPath(), scn.targetJavaFile.toPath());
					Files.copy(scn.classBackup.toPath(), scn.targetClassFile.toPath());
				} catch (IOException e) {
					e.printStackTrace();
				}
				continue;
			}
			this.triedPatchCandidates.add(patch);
			String loopId=this.isSecondLoop? "1":"0";
			String mutatorName=patch.mutator.getSimpleName();
			String fixedDir="d4j/"+buggyProject+"/"+loopId+"/"+Integer.toString(scn.rank)+"/"+
						mutatorName+"/"+Integer.toString(patch.id)+"/";
			log.info(fixedDir);
			String fixedPath=fixedDir+scn.suspiciousJavaFile;

			List<String> dirs=Arrays.asList(fixedPath.split("/"));
			String sourceFile=dirs.get(dirs.size()-1);
			sourceFile=removeInnerClassFromSourcePath(sourceFile);

			String patchID=loopId+"/"+Integer.toString(scn.rank)+"/"+
						mutatorName+"/"+Integer.toString(patch.id)+"/"+sourceFile;
			
			boolean isCompilable=true;
			String buggyCode = patch.getBuggyCodeStr();
			if ("===StringIndexOutOfBoundsException===".equals(buggyCode)) continue;
			String patchCode = patch.getFixedCodeStr1();
			scn.targetClassFile.delete();

			log.info("Compiling");
			long startTime=Calendar.getInstance().getTimeInMillis();
			try {// Compile patched file.
				ShellUtils.shellRun(Arrays.asList("javac -Xlint:unchecked -source 1.7 -target 1.7 -cp "
						+ PathUtils.buildCompileClassPath(Arrays.asList(PathUtils.getJunitPath()), dp.classPath, dp.testClassPath)
						+ " -d " + dp.classPath + " " + scn.targetJavaFile.getAbsolutePath()), buggyProject);
			} catch (IOException e) {
				long finishTime=Calendar.getInstance().getTimeInMillis();
				log.info(buggyProject + " ---Fixer: fix fail because of javac exception! ");
				CacheInfo.Cache cache=new CacheInfo.Cache(patchID,false,(finishTime-startTime)/1000);
				if (!cacheInfo.isCached(cache)) cacheInfo.appendCache(cache);

				File patchDir=new File(fixedDir);
				try {
					org.apache.commons.io.FileUtils.deleteDirectory(patchDir);
				} catch (IOException e1) {
					e1.printStackTrace();
				}

				continue;
			}
			if (!scn.targetClassFile.exists()) { // fail to compile
				long finishTime=Calendar.getInstance().getTimeInMillis();
				log.info(buggyProject + " ---Fixer: fix fail because of failed compiling! ");
				CacheInfo.Cache cache=new CacheInfo.Cache(patchID,false,(finishTime-startTime)/1000);
				if (!cacheInfo.isCached(cache)) cacheInfo.appendCache(cache);

				File patchDir=new File(fixedDir);
				try {
					org.apache.commons.io.FileUtils.deleteDirectory(patchDir);
				} catch (IOException e) {
					e.printStackTrace();
				}

				continue;
			}
			log.info("Finish of compiling.");
			
			log.debug("Test previously failed test cases.");
			boolean isPassed=false;
			try{
				for (String test:this.failedTestCasesStrList){
					String command="defects4j test -w "+path + buggyProject+" -t "+test;
					String results = ShellUtils.shellRun(Arrays.asList(command), buggyProject);
					List<String> tempFailedTestCases = readTestResults(results);

					if (!tempFailedTestCases.contains(test)){
						isPassed=true;
						break;
					}
				}
				
				if (isPassed) {
					log.info(buggyProject + " ---Fixer: Success to pass failed test ");
					// Don't add to cache partially fixed (basic patch).
				}
				else{
					log.info(buggyProject + " ---Fixer: Fail to pass failed test ");
					long finishTime=Calendar.getInstance().getTimeInMillis();
					CacheInfo.Cache cache=new CacheInfo.Cache(patchID,true,(finishTime-startTime)/1000);
					if (!cacheInfo.isCached(cache)) cacheInfo.appendCache(cache);

					File patchDir=new File(fixedDir);
					org.apache.commons.io.FileUtils.deleteDirectory(patchDir);
				}
			}
			catch(Exception e){
				log.info(buggyProject + " ---Fixer: Exception in running test ");
				long finishTime=Calendar.getInstance().getTimeInMillis();
				CacheInfo.Cache cache=new CacheInfo.Cache(patchID,true,(finishTime-startTime)/1000);
				if (!cacheInfo.isCached(cache)) cacheInfo.appendCache(cache);

				File patchDir=new File(fixedDir);
				try {
					org.apache.commons.io.FileUtils.deleteDirectory(patchDir);
				} catch (IOException e1) {
					e1.printStackTrace();
				}
			}

			// List<String> failedTestsAfterFix = new ArrayList<>();
			// int errorTestAfterFix = TestUtils.getFailTestNumInProject(fullBuggyProjectPath, this.defects4jPath,
			// 		failedTestsAfterFix);
			// failedTestsAfterFix.removeAll(this.fakeFailedTestCasesList);
			
			// if (errorTestAfterFix < minErrorTest) {
			// 	failedTestsAfterFix.removeAll(this.failedTestStrList);
			// 	if (failedTestsAfterFix.size() > 0) { // Generate new bugs.
			// 		log.debug(buggyProject + " ---Generated new bugs: " + failedTestsAfterFix.size());
			// 		continue;
			// 	}
				
			// 	// Output the generated patch.
			// 	if (errorTestAfterFix == 0) {
			// 		fixedStatus = 1;
			// 		log.info("Succeeded to fix the bug " + buggyProject + "====================");
			// 		String patchStr = TestUtils.readPatch(this.fullBuggyProjectPath);
			// 		if (patchStr == null || !patchStr.startsWith("diff")) {
			// 			FileHelper.outputToFile("OUTPUT/FixedBugs/" + buggyProject + "/Patch_" + patchId + ".txt",
			// 					"//**********************************************************\n//" + scn.suspiciousJavaFile + " ------ " + scn.buggyLine
			// 					+ "\n//**********************************************************\n"
			// 					+ "===Buggy Code===\n" + buggyCode + "\n\n===Patch Code===\n" + patchCode, false);
			// 		} else {
			// 			FileHelper.outputToFile("OUTPUT/FixedBugs/" + buggyProject + "/Patch_" + patchId + ".txt", patchStr, false);
			// 		}
			// 		this.minErrorTest = 0;
			// 		break;
			// 	} else {
			// 		if (minErrorTestAfterFix == 0 || errorTestAfterFix <= minErrorTestAfterFix) {
			// 			minErrorTestAfterFix = errorTestAfterFix;
			// 			if (fixedStatus != 1) fixedStatus = 2;
			// 			log.info("Partially Succeeded to fix the bug " + buggyProject + "====================");
			// 			String patchStr = TestUtils.readPatch(this.fullBuggyProjectPath);
			// 			if (patchStr == null || !patchStr.startsWith("diff")) {
			// 				FileHelper.outputToFile("OUTPUT/FixedBugs/" + buggyProject + "/Patch_" + patchId + ".txt",
			// 						"//**********************************************************\n//" + scn.suspiciousJavaFile + " ------ " + scn.buggyLine
			// 						+ "\n//**********************************************************\n"
			// 						+ "===Buggy Code===\n" + buggyCode + "\n\n===Patch Code===\n" + patchCode, false);
			// 			} else {
			// 				FileHelper.outputToFile("OUTPUT/FixedBugs/" + buggyProject + "/Patch_" + patchId + ".txt", patchStr, false);
			// 			}
			// 		}
			// 	}
			// } else {
			// 	log.debug("Failed Tests after fixing: " + errorTestAfterFix + " " + buggyProject);
			// }
		}
		
		try {
			scn.targetJavaFile.delete();
			scn.targetClassFile.delete();
			Files.copy(scn.javaBackup.toPath(), scn.targetJavaFile.toPath());
			Files.copy(scn.classBackup.toPath(), scn.targetClassFile.toPath());
		} catch (IOException e1) {
			e1.printStackTrace();
		}
	}
	
	private List<String> readTestResults(String results) {
		List<String> failedTeatCases = new ArrayList<>();
		String[] testResults = results.split("\n");
		for (String testResult : testResults) {
			if (testResult.isEmpty()) continue;
			
			if (testResult.contains("  - ")){
				String failedTest = testResult.substring(4);
				failedTeatCases.add(failedTest);
			}
		}
		return failedTeatCases;
	}

	private void addPatchCodeToFile(SuspCodeNode scn, Patch patch,String outputPath) {
		String javaCode = FileHelper.readFile(scn.javaBackup);
        
		String fixedCodeStr1 = patch.getFixedCodeStr1();
		String fixedCodeStr2 = patch.getFixedCodeStr2();
		int exactBuggyCodeStartPos = patch.getBuggyCodeStartPos();
		int exactBuggyCodeEndPos = patch.getBuggyCodeEndPos();
		String patchCode = fixedCodeStr1;
		boolean needBuggyCode = false;
		if (exactBuggyCodeEndPos > exactBuggyCodeStartPos) {
			if ("MOVE-BUGGY-STATEMENT".equals(fixedCodeStr2)) {
				// move statement position.
			} else if (exactBuggyCodeStartPos != -1 && exactBuggyCodeStartPos < scn.startPos) {
				// Remove the buggy method declaration.
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
					// Insert a block-held statement to surround the buggy code
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
		try {
			buggyCode = javaCode.substring(exactBuggyCodeStartPos, exactBuggyCodeEndPos);
			if (needBuggyCode) {
	        	patchCode += buggyCode;
	        	if (fixedCodeStr2 != null) {
	        		patchCode += fixedCodeStr2;
	        	}
	        }
			
			if (outputPath.equals("")){
				// Save to source code, if output path not specified
				File newFile = new File(scn.targetJavaFile.getAbsolutePath() + ".temp");
				String patchedJavaFile = javaCode.substring(0, exactBuggyCodeStartPos) + patchCode + javaCode.substring(exactBuggyCodeEndPos);
				FileHelper.outputToFile(newFile, patchedJavaFile, false);
				newFile.renameTo(scn.targetJavaFile);
			}
			else{
				File newFile = new File(outputPath);
				String patchedJavaFile = javaCode.substring(0, exactBuggyCodeStartPos) + patchCode + javaCode.substring(exactBuggyCodeEndPos);
				FileHelper.outputToFile(newFile, patchedJavaFile, false);
			}
		} catch (StringIndexOutOfBoundsException e) {
			log.debug(exactBuggyCodeStartPos + " ==> " + exactBuggyCodeEndPos + " : " + javaCode.length());
			e.printStackTrace();
			buggyCode = "===StringIndexOutOfBoundsException===";
		}
        
        patch.setBuggyCodeStr(buggyCode);
        patch.setFixedCodeStr1(patchCode);
	}

	private void addPatchCodeToFile(SuspCodeNode scn, Patch patch){
		addPatchCodeToFile(scn, patch, "");
	}
	
	class SuspCodeNode {

		public File javaBackup;
		public File classBackup;
		public File targetJavaFile;
		public File targetClassFile;
		public int startPos;
		public int endPos;
		public ITree suspCodeAstNode;
		public String suspCodeStr;
		public String suspiciousJavaFile;
		public int buggyLine;
		public double flScore;
		public int rank;
		
		public SuspCodeNode(File javaBackup, File classBackup, File targetJavaFile, File targetClassFile, int startPos,
				int endPos, ITree suspCodeAstNode, String suspCodeStr, String suspiciousJavaFile, int buggyLine,double flScore,int rank) {
			this.javaBackup = javaBackup;
			this.classBackup = classBackup;
			this.targetJavaFile = targetJavaFile;
			this.targetClassFile = targetClassFile;
			this.startPos = startPos;
			this.endPos = endPos;
			this.suspCodeAstNode = suspCodeAstNode;
			this.suspCodeStr = suspCodeStr;
			this.suspiciousJavaFile = suspiciousJavaFile;
			this.buggyLine = buggyLine;
			this.flScore=flScore;
			this.rank=rank;
		}

		@Override
		public boolean equals(Object obj) {
			if (obj == null) return false;
			if (obj instanceof SuspCodeNode) {
				SuspCodeNode suspN = (SuspCodeNode) obj;
				if (startPos != suspN.startPos) return false;
				if (endPos != suspN.endPos) return false;
				if (suspiciousJavaFile.equals(suspN.suspiciousJavaFile)) return true;
			}
			return false;
		}
	}
}
