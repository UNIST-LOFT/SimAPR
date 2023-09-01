package edu.lu.uni.serval.tbar;

import edu.lu.uni.serval.entity.Pair;
import edu.lu.uni.serval.jdt.tree.ITree;
import edu.lu.uni.serval.tbar.code.analyser.JavaCodeFileParser;
import edu.lu.uni.serval.tbar.config.Configuration;
import edu.lu.uni.serval.tbar.context.ContextReader;
import edu.lu.uni.serval.tbar.context.Dictionary;
import edu.lu.uni.serval.tbar.dataprepare.DataPreparerExtended;
import edu.lu.uni.serval.tbar.fixpatterns.*;
import edu.lu.uni.serval.tbar.fixtemplate.FixTemplate;
import edu.lu.uni.serval.tbar.info.Patch;
import edu.lu.uni.serval.tbar.utils.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;

public class TBarTransformerFixer implements IFixer {

    public enum Granularity {
		Line,
		File,
		FL
	}

    private Dictionary dictionary = null;
	public static String dataType = "/TBarTransformer";

    private static Logger log = LoggerFactory.getLogger(TBarTransformerFixer.class);

    private final String bugJavaPath; // Example: src/{path_to_file}/Dummy.java
    private final int bugLineNumber; // Example: 154...
    private final String targetProject; // Example: D4j/projects/
	private final String targetProjectName; // test

	private final DataPreparerExtended dataPreparer;

    public TBarTransformerFixer(String bugFileLocation, int bugLine, String projectPath, String projectName) {
        this.bugJavaPath = bugFileLocation;
        this.bugLineNumber = bugLine;
        this.targetProject = projectPath;
		this.targetProjectName = projectName;
		this.dataPreparer = new DataPreparerExtended(projectPath);
		this.dataPreparer.prepareData(projectName);

		log.info("Init bugJavaPath => " + this.bugJavaPath);
		log.info("Init bugLineNumber => " + this.bugLineNumber);
		log.info("Init targetProject => " + this.targetProject);
		log.info("Init targetProjectName => " + this.targetProjectName);
    }

    @Override
    public void fixProcess() {
        log.info("======= Applying some transformers =======");

        List<SuspiciousPosition> positions = readSuspiciousCodeFromFile();
        List<SuspCodeNode> triedSuspNode = new ArrayList<>();
        for (SuspiciousPosition position: positions) {
            List<SuspCodeNode> scns = parseSuspiciousCode(position);
            if (scns == null) continue;

			for (int i = 0; i < scns.size(); i++) {
				SuspCodeNode scn = scns.get(i);
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
                fixWithMatchedFixTemplates(scn, distinctContextInfo, i);
			}
        }
        log.info("======= TBarTransformer: Finish off transforming ======");

    }

    /*
    Initially its modeled to read suspicious positions from some storage file.
    But for the purpose of testing we add it manually.
    */
    @Override
    public List<SuspiciousPosition> readSuspiciousCodeFromFile() {
        List<SuspiciousPosition> positions = new ArrayList<>();

        // Custom made one line of suspicious bug position
        SuspiciousPosition position = new SuspiciousPosition();
		String shortSrcPath = dataPreparer.srcPath.substring(dataPreparer.srcPath.indexOf(this.targetProjectName) + this.targetProjectName.length() + 1);
        position.classPath = this.bugJavaPath.substring(shortSrcPath.length(), this.bugJavaPath.length() - 5);
        position.lineNumber = this.bugLineNumber;
        positions.add(position);

		log.info("Reading shortsourcepath from file: " + shortSrcPath);
		log.info("Parsing classPath from file: " + position.classPath);
		log.info("Parsing lineNumber from file: " + position.lineNumber);

        if (positions.isEmpty()) {
            log.error("Could not find any suspicious position in target projecs " + "{add your text}");
            return null;
        }
        return positions;
    }

    @Override
    public List<SuspCodeNode> parseSuspiciousCode(SuspiciousPosition suspiciousCode) {
        String suspClassPath = suspiciousCode.classPath;
        int suspLine = suspiciousCode.lineNumber;

        log.info("Parsing suspicious file: " + suspClassPath + "@" + suspLine);

		String filePath = dataPreparer.srcPath;
        File suspCodeFile = new File(filePath);
        if (!suspCodeFile.exists()) {
            log.error("File " + suspClassPath +" does not exist");
            return null;
        }
        SuspiciousCodeParser scp = new SuspiciousCodeParser();
		scp.parseSuspiciousCode(suspCodeFile, suspLine);
        List<Pair<ITree, String>> suspiciousCodePairs = scp.getSuspiciousCode();
        if (suspiciousCodePairs.isEmpty()) {
			log.error("Failed to identify the buggy statement in: " + "@" + suspLine);
			return null;
		}
		String targetJavaFilePath = FileUtils.getFileAddressOfJava(dataPreparer.srcPath, suspClassPath);
		String targetClassFilePath = FileUtils.getFileAddressOfClass(dataPreparer.classPath, suspClassPath);
		String identifier = "";
		String javaBackupPath = FileUtils.tempJavaPath(suspClassPath,  identifier);
		String classBackupPath = FileUtils.tempClassPath(suspClassPath, identifier);
        File targetJavaFile = new File(targetJavaFilePath);
        File targetClassFile = new File(targetClassFilePath);
        File javaBackup = new File(javaBackupPath);
        File classBackup = new File(classBackupPath);

		log.info(
			"=== Backup process === \n" +
			"Target java file: " + targetJavaFilePath + "\n" +
			"Target class file: " + targetClassFilePath + "\n" +
			"Java file backup: " + javaBackupPath + "\n" +
			"Class file backup: " + classBackupPath
		);

        try {
        	if (!targetClassFile.exists()) return null;
        	if (javaBackup.exists()) javaBackup.delete();
        	if (classBackup.exists()) classBackup.delete();
			Files.copy(targetJavaFile.toPath(), javaBackup.toPath());
			Files.copy(targetClassFile.toPath(), classBackup.toPath());
		} catch (IOException e) {
			log.error(e.getMessage());
		}

        List<SuspCodeNode> scns = new ArrayList<>();
        for (Pair<ITree, String> suspCodePair : suspiciousCodePairs) {
			ITree suspCodeAstNode = suspCodePair.getFirst(); //scp.getSuspiciousCodeAstNode();
			String suspCodeStr = suspCodePair.getSecond(); //scp.getSuspiciousCodeStr();

			log.info("===== Suspicious Code ===== \n" + suspCodeStr);

            int startPos = suspCodeAstNode.getPos();
			int endPos = startPos + suspCodeAstNode.getLength();
            SuspCodeNode scn = new SuspCodeNode(
                javaBackup,
                classBackup,
                targetJavaFile,
                targetClassFile,
                startPos,
                endPos,
                suspCodeAstNode,
                suspCodeStr,
                "",
                suspLine,
				0.1,
				0
            );
			scns.add(scn);
		}
        return scns;
    }

    public List<Integer> readAllNodeTypes(ITree suspCodeAstNode) {
		List<Integer> nodeTypes = new ArrayList<>();
		nodeTypes.add(suspCodeAstNode.getType());
		List<ITree> children = suspCodeAstNode.getChildren();
		for (ITree child : children) {
			int childType = child.getType();
			if (Checker.isFieldDeclaration(childType) ||
					Checker.isMethodDeclaration(childType) ||
					Checker.isTypeDeclaration(childType) ||
					Checker.isStatement(childType)) break;
			nodeTypes.addAll(readAllNodeTypes(child));
		}
		return nodeTypes;
	}

    public void fixWithMatchedFixTemplates(SuspCodeNode scn, List<Integer> distinctContextInfo, int index) {
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
						generateAndValidatePatches(ft, scn, index);
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
						generateAndValidatePatches(ft, scn, index);
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
					generateAndValidatePatches(ft, scn, index);
					if (!operator) {
						operator = true;
						ft = new OperatorMutator(0);
						generateAndValidatePatches(ft, scn, index);
					}

					ft = new ConditionalExpressionMutator(1);
					generateAndValidatePatches(ft, scn, index);
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
							generateAndValidatePatches(ft, scn, index);
						}
						ft = new NPEqualsShouldHandleNullArgument();
						generateAndValidatePatches(ft, scn, index);
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
						generateAndValidatePatches(ft, scn, index);
						nullChecked = true;
						ft = new NullPointerChecker();
					}
				}
				if (ft != null) {
					generateAndValidatePatches(ft, scn, index);
				}
				ft = null;
			}

			if (!nullChecked) {
				nullChecked = true;
				ft = new NullPointerChecker();
				generateAndValidatePatches(ft, scn, index);
			}

			ft = new StatementMover();
			generateAndValidatePatches(ft, scn, index);

			ft = new StatementRemover();
			generateAndValidatePatches(ft, scn, index);

			ft = new StatementInserter();
			generateAndValidatePatches(ft, scn, index);
		} else {
			ft = new StatementRemover();
			generateAndValidatePatches(ft, scn, index);
		}
	}

    protected void generateAndValidatePatches(FixTemplate ft, SuspCodeNode scn, int index) {
		ft.setSuspiciousCodeStr(scn.suspCodeStr);
		ft.setSuspiciousCodeTree(scn.suspCodeAstNode);
		if (scn.javaBackup == null) ft.setSourceCodePath(dataPreparer.srcPath);
		else ft.setSourceCodePath(dataPreparer.srcPath, scn.javaBackup);
		ft.setDictionary(this.dictionary);
		ft.generatePatches();
		List<Patch> patchCandidates = ft.getPatches();
		// Test generated patches.
		if (patchCandidates.isEmpty()) return;
		saveGeneratedPatches(patchCandidates, scn, index, ft.getClass().getSimpleName());
	}

    private void createDictionary() {
		this.dictionary = new Dictionary();
		List<File> javaFiles = FileHelper.getAllFiles(this.targetProject, ".java");
		for (File javaFile : javaFiles) {
			JavaCodeFileParser jcfp = new JavaCodeFileParser(javaFile);
			this.dictionary.setAllFields(jcfp.fields);
			this.dictionary.setImportedDependencies(jcfp.importMaps);
			this.dictionary.setMethods(jcfp.methods);
			this.dictionary.setSuperClasses(jcfp.superClassNames);
		}
	}

    private void saveGeneratedPatches(List<Patch> patchCandidates, SuspCodeNode scn, int index, String fixname) {
		for (int i = 0; i < patchCandidates.size(); i++) {
            Patch patch = patchCandidates.get(i);
			patch.buggyFileName = scn.suspiciousJavaFile;
            String location = addPatchCodeToFile(scn, patch, index, fixname, i);
			String buggyCode = patch.getBuggyCodeStr();
			if ("===StringIndexOutOfBoundsException===".equals(buggyCode)) continue;
			String patchCode = patch.getFixedCodeStr1();

			log.info("Buggy Code: \n" + buggyCode + "\n Patched Code: \n" + patchCode);

			// Json logs
			int startPosition = patch.getBuggyCodeStartPos();
			int endPosition = patch.getBuggyCodeEndPos();
			String javafile = scn.targetJavaFile.getAbsolutePath().substring(0, scn.targetJavaFile.getAbsolutePath().length() - 5);
		}
    }

    private String addPatchCodeToFile(SuspCodeNode scn, Patch patch, int index, String fixname, int patchId) {
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
		File tempNewFile = null;
		try {
			buggyCode = javaCode.substring(exactBuggyCodeStartPos, exactBuggyCodeEndPos);
			if (needBuggyCode) {
	        	patchCode += buggyCode;
	        	if (fixedCodeStr2 != null) {
	        		patchCode += fixedCodeStr2;
	        	}
	        }
			String patchSuffix = "_" + index + "_" + fixname + patchId;
			String targetFilePath = scn.targetJavaFile.getAbsolutePath().substring(0, scn.targetJavaFile.getAbsolutePath().length() - 5);
			File newFile = new File(targetFilePath + patchSuffix + ".java");
			tempNewFile = new File(Configuration.TEMP_PATCHES_FILES_PATH + patchSuffix + "/" + scn.targetJavaFile.getName());
	        String patchedJavaFile = javaCode.substring(0, exactBuggyCodeStartPos) + patchCode + javaCode.substring(exactBuggyCodeEndPos);
	        FileHelper.outputToFile(newFile, patchedJavaFile, false);
			FileHelper.outputToFile(tempNewFile, patchedJavaFile, false);
			try {
				newFile.createNewFile();
				tempNewFile.createNewFile();
			} catch (Exception e) {
				log.error("Couldn't create new file:", e);
			}

//			compilePatch("javac -Xlint:unchecked -source 1.7 -target 1.7 -cp "
//			+ PathUtils.buildCompileClassPath(Arrays.asList(PathUtils.getJunitPath()), dataPreparer.classPath, dataPreparer.testClassPath)
//			+ " " + tempNewFile.getAbsolutePath());

	        // newFile.renameTo(scn.targetJavaFile);
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

}