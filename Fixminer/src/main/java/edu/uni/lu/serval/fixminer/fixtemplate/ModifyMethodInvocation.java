package edu.uni.lu.serval.fixminer.fixtemplate;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import edu.lu.uni.serval.AST.ASTGenerator;
import edu.lu.uni.serval.AST.ASTGenerator.TokenType;
import edu.lu.uni.serval.fixminer.ProjectLiteral;
import edu.lu.uni.serval.jdt.tree.ITree;
import edu.lu.uni.serval.templates.AlterMethodInvocation;
import edu.lu.uni.serval.utils.Checker;

/**
 * 
 * @author kui.liu
 *
 */
public class ModifyMethodInvocation extends AlterMethodInvocation {

	private ITree suspCodeAst;
	private int suspCodeStartPos;
	private int suspCodeEndPos;
	
	public enum ModifyType {
		/*
		 * ---UPD MethodInvocation
		 * ------UPD SimpleName
		 * ---------DEL/INS/UPD SimpleName
		 */
		VarArgument,
		
		/*
		 * ---UPD MethodInvocation
		 * ------UPD SimpleName@@MethodName
		 * ---------DEL SimpleName
		 * ---------INS MethodInvocation@@job.getConfiguration()
		 * ------------INS SimpleName@@Name
		 * ------------INS SimpleName@@MethodName
		 */
		VarArgument2Method,
		
		/*
		 * ---UPD MethodInvocation
		 * ------UPD SimpleName@@MethodName
		 * ---------UPD QualifiedName@@Calendar.HOUR
		 * ------------UPD SimpleName@@HOUR
		 */
		SubVarArgument,
		
		/*
		 * ---UPD MethodInvocation
		 * ------UPD SimpleName
		 * ---------UPD/INS/DEL BooleanLiteral
		 */
		BoolArgument,
		
		/*
		 * ---UPD MethodInvocation
		 * ------UPD SimpleName
		 * ---------UPD StringLiteral parameter
		 */
		StringArgument,
		
		/*
		 * ---UPD MethodInvocation
		 * ------UPD SimpleName(Method name)
		 * ---------UPD InfixExpression
		 * ------------UPD StringLiteral
		 */
		InfixStringArgument,
		
		/*
		 * ---UPD MethodInvocation
		 * ------UPD SimpleName@@MethodName
		 * ---------UPD NumberLiteral
		 */
		NumberArgument,
		
		/*
		 * ---UPD MethodInvocation
		 * ------UPD SimpleName(method name)
		 */
		MethodName,
		
		/*
		 * ---UPD MethodInvocation
		 * ------UPD MethodInvocation(method name)
		 * e.g., exp.method1().method2() --> exp.method().method2().
		 */
		MidMethodName,
		
		/*
		 * ---UPD MethodInvocation@@xstream.omitField(type,fieldName) @TO@ getXStream().omitField(type,fieldName)
		 * ------DEL SimpleName@@Name:xstream 
		 * ------INS MethodInvocation@@MethodName:getXStream:[] @TO@ MethodInvocation@@xstream.omitField(type,fieldName) 
		 * e.g., var.method1() --> method().method1().
		 */
		VarReference2Method,
		
		/*
		 * ---UPD MethodInvocation
		 * ------UPD SimpleNam
		 */
		VarReference2VarRef,
		
		/*
		 * ---UPD MethodInvocation
		 * ------UPD SimpleName(method name)
		 * ---------UPD MethodInvocation
		 * ------------UPD SimpleName(method name)
		 */
		SumMethodInvocation,
		
		DEFAULT
	}

	protected ITree suspMethodInvocationTree = null; 
	protected ModifyType modifyType = ModifyType.DEFAULT;
	protected String returnTypeStr = "";
	
	public ModifyMethodInvocation(ITree suspMethodInvocationTree, ModifyType modifyType) {
		this.suspMethodInvocationTree = suspMethodInvocationTree;
		this.modifyType = modifyType;
		suspMethodInvocations.clear();
	}
	
	@Override
	public void generatePatches() {
		
		suspCodeAst = getSuspiciousCodeTree();
		suspCodeStartPos = suspCodeAst.getPos();
		suspCodeEndPos = suspCodeStartPos + suspCodeAst.getLength();
		if (modifyType == null) {
			defaultFixManner();
			return;
		}
		switch (modifyType) {
		case VarArgument: // DEL/INS/UPD SimpleName (variable name).
			new ModifyMethodVarArgument().generatePatches(suspMethodInvocationTree);
			break;
		case VarArgument2Method: // method(var) --> method(var1.method1());
			new ModifyMethodVarArgument2MethodInv().generatePatches(suspMethodInvocationTree);
			break;
		case SubVarArgument:
			new ModifyMethodQualifiedVarArgument().generatePatches(suspMethodInvocationTree);
			break;
		case BoolArgument:
			new ModifyMethodBoolArgument().generatePatches(suspMethodInvocationTree);
			break;
		case StringArgument:
			new ModifyMethodStringArgument().generatePatches(suspMethodInvocationTree);
			break;
		case InfixStringArgument:
			new ModifyMethodInfixStringArgument().generatePatches(suspMethodInvocationTree);
			break;
		case NumberArgument:
			new ModifyMethodNumberArgument().generatePatches(suspMethodInvocationTree);
			break;
		case MethodName:
			new ModifyMethodName().generatePatches(suspMethodInvocationTree, returnTypeStr);
			break;
		case MidMethodName:
			new MethodMidMethodName().generatePatches(suspMethodInvocationTree);
			break;
		case VarReference2Method:
			new ModifyMethodVarReference2Method().generatePatches(suspMethodInvocationTree);
			break;
		case VarReference2VarRef:
			new ModifyMethodVarReference2VarRef().generatePatches(suspMethodInvocationTree);
			break;
		case SumMethodInvocation: // See case MethodName:
			/*
			 * ---UPD MethodInvocation
			 * ------UPD SimpleName(method name)
			 * ---------UPD MethodInvocation
			 * ------------UPD SimpleName(method name)
			 */
			break;
		default:
			defaultFixManner();
			break;
		}
	}
	
	private void defaultFixManner() {
		List<ITree> methodInvocations = identifyAllMethodInvocations(suspMethodInvocationTree);
		for (ITree methodInvocation : methodInvocations) {
			new ModifyMethodVarArgument().generatePatches(methodInvocation);
			new ModifyMethodVarArgument2MethodInv().generatePatches(methodInvocation);
			new ModifyMethodQualifiedVarArgument().generatePatches(methodInvocation);
			new ModifyMethodBoolArgument().generatePatches(methodInvocation);
			new ModifyMethodStringArgument().generatePatches(methodInvocation);
			new ModifyMethodInfixStringArgument().generatePatches(methodInvocation);
			new ModifyMethodNumberArgument().generatePatches(methodInvocation);
			new ModifyMethodName().generatePatches(methodInvocation, "");
			new MethodMidMethodName().generatePatches(methodInvocation);
			new ModifyMethodVarReference2Method().generatePatches(methodInvocation);
		}
	}

	private List<ITree> identifyAllMethodInvocations(ITree codeAst) {
		List<ITree> methodInvocations = new ArrayList<>();
		List<ITree> children = codeAst.getChildren();
		for (ITree child : children) {
			int type = child.getType();
			if (Checker.isComplexExpression(type)) {
				methodInvocations.addAll(identifyAllMethodInvocations(child));
				if (Checker.isMethodInvocation(type)) {
					methodInvocations.add(child);
				}
			} else if (Checker.isSimpleName(type)) break;
		}
		return methodInvocations;
	}

	protected List<MethodInvocationExpression> identifySuspiciousMethodInvocations(String returnTypeStr) {
		varTypesMap.clear();
		allVarNamesList.clear();
		allVarNamesMap = readAllVariableNames(suspCodeAst, varTypesMap, allVarNamesList);
		
		if (classDeclarationAst == null) {
			readClassDeclaration(suspCodeAst);
		}
		if (className == null) {
			readClassName(suspCodeAst);
			readPackageName();
		}
		
		return identifySuspiciousMethodInvocations1(returnTypeStr);
	}
	
	/**
	 * Read the information of suspicious method invocations.
	 * @return
	 */
	private List<MethodInvocationExpression> identifySuspiciousMethodInvocations1(String returnType) {
		List<MethodInvocationExpression> suspMethodInvocationsList = new ArrayList<>();
		
		for (Map.Entry<ITree, Integer> entry : suspMethodInvocations.entrySet()) {
			int type = entry.getValue();
			ITree methodNameNode = entry.getKey();
			
			// Read method name and parameters.
			// Read the possible return types of the method.
			ITree rootTree = null;
			String varType = null;
			String methodName = null;
			List<ITree> parameters = null;
			
			if (type == 2) {
				List<ITree> children1 = methodNameNode.getChildren();
				methodNameNode = children1.get(children1.size() - 1);
			}
			parameters = methodNameNode.getChildren();
			methodName = methodNameNode.getLabel().substring(11);
			methodName = methodName.substring(0, methodName.indexOf(":"));
				
			ITree parentCodeAst = methodNameNode.getParent();
			int indexPos = parentCodeAst.getChildPosition(methodNameNode);
			if (indexPos == 0) { // the method belongs to the current class or its ancestral classes.
				rootTree = classDeclarationAst;
				varType = "this";
			} else { // the method belongs to the class of the return data type of its previous peer AST node..
				ITree prePeerCodeAst = parentCodeAst.getChild(indexPos - 1);
				/*
				 * The previous peer AST node can be:
				 * 		a. field
				 * 		b. qualified name.
				 * 		c. method invocation.
				 * 		d. other complex expressions.
				 */
				int prePeerCodeAstType = prePeerCodeAst.getType();
				if (Checker.isSimpleName(prePeerCodeAstType)) { // a variable.
					String varName = readVariableName2(prePeerCodeAst);
					varType = varTypesMap.get(varName);
					if (varType == null) varType = varTypesMap.get("this." + varName);
					if (varType == null) varType = varName;
					rootTree = classDeclarationAst;
				} else if (Checker.isQualifiedName(prePeerCodeAstType)) { 
					// QualifiedName: T.var.get()
					String dataType = prePeerCodeAst.getLabel(); 
					if (varTypesMap.containsKey(dataType)) {
						varType = varTypesMap.get(dataType);
						rootTree = classDeclarationAst;
					} else {
						int firstPointIndex = dataType.indexOf(".");
						String fieldName = dataType.substring(firstPointIndex + 1); // Class name.
						dataType = dataType.substring(0, firstPointIndex);
						String dataTypeFile = identifyJavaFilePath(classDeclarationAst, dataType);
						if (dataTypeFile != null) { // field data type.
							rootTree = new ASTGenerator().generateTreeForJavaFile(dataTypeFile, TokenType.EXP_JDT);
							List<ITree> children = rootTree.getChildren();
							children = children.get(children.size() - 1).getChildren();
							for (ITree child : children) {
								if (Checker.isFieldDeclaration(child.getType())) { // Field declaration
									List<ITree> subChildren = child.getChildren();
									boolean isFound = false;
									for (int i = 1, size = subChildren.size(); i < size; i ++) {
										ITree varDeclaration = subChildren.get(i);
										if (Checker.isVariableDeclarationFragment(varDeclaration.getType())) {
											if (varType == null) varType = subChildren.get(i - 1).getLabel();
											if (varDeclaration.getChild(0).getLabel().equals(fieldName)) {
												isFound = true;
												break;
											}
										}
									}
									if (isFound) break;
									varType = null;
								}
							}
						}
					}
				} else if (Checker.isFieldAccess(prePeerCodeAstType)
						|| Checker.isSuperFieldAccess(prePeerCodeAstType)) {
					// FieldAccess: this.var.get();
					// SuperFieldAccess: super.var.get();
					List<ITree> subChildren = prePeerCodeAst.getChildren();
					String dataType = subChildren.get(subChildren.size() - 1).getLabel();
					varType = varTypesMap.get(dataType);
					if (varType == null) varType = varTypesMap.get("this." + dataType);
					rootTree = classDeclarationAst;
					if (varType == null) {
						// TODO: is it possible to be null?
						continue;
					}
				} else if (Checker.isMethodInvocation(prePeerCodeAstType)) {
					// TODO the return type of the previous peer method invocation.
					continue;
				} else {
					// FIXME: other possible expressions.
					continue;
				}
			}

			if (rootTree == null || varType == null) continue;
			
			// Read parameter data types.
			List<String> paraTypeStrs = readMethodParameterTypes(parameters);
			if (paraTypeStrs == null) continue; // Generate ERROR when reading its parameter types.
			
			if ("=ReturnType=".equals(returnType)) returnType = identifyReturnType();
			if (returnType == null) continue;
			
			// Identify possible return types of the method invocations.
			Map<List<String>, String> map = identifyPossibleReturnTypes(rootTree, varType, methodName, paraTypeStrs);
			List<String> possibleReturnTypes = null;
			String methodClassPath = null;
			if (map != null) {
				for (Map.Entry<List<String>, String> subEntry : map.entrySet()) {
					possibleReturnTypes = subEntry.getKey();
					methodClassPath = subEntry.getValue();
					break;
				}
			}
			
			if (possibleReturnTypes != null && !possibleReturnTypes.isEmpty()) {
				MethodInvocationExpression mi = new MethodInvocationExpression();
				mi.setCodePath(methodClassPath);
				mi.setMethodName(methodName);
				mi.setCodeAst(methodNameNode);
				mi.setDifferentParaMethods(differentParaMethods);
				mi.setCouldBeReplacedMethods(couldBeReplacedMethods);
				for (String possibleReturnType : possibleReturnTypes) {
					String[] elements = possibleReturnType.split("\\+");
					if ("=Void=".equals(returnType) || "".equals(returnType)) {
						mi.getPossibleReturnTypes().add(elements[0]);
						paraTypeStrs = new ArrayList<>();
						for (int i = 1, length = elements.length; i < length; i = i + 2) {
							paraTypeStrs.add(elements[i]);
						}
						mi.getParameterTypes().add(paraTypeStrs);
					} else if (elements[0].equals(returnType)) {
						mi.getPossibleReturnTypes().add(elements[0]);
						paraTypeStrs = new ArrayList<>();
						for (int i = 1, length = elements.length; i < length; i = i + 2) {
							paraTypeStrs.add(elements[i]);
						}
						mi.getParameterTypes().add(paraTypeStrs);
					}
				}
				suspMethodInvocationsList.add(mi);
			}
		}
		return suspMethodInvocationsList;
	}
	
	private String identifyReturnType() {
		ITree suspCodeTree = getSuspiciousCodeTree();
		ITree parentTree = suspCodeTree.getParent();
		while (true) {
			if (Checker.isMethodDeclaration(parentTree.getType()))
				break;
			if (Checker.isTypeDeclaration(parentTree.getType())) {
				parentTree = null;
				break;
			}
			parentTree = parentTree.getParent();
		}
		
		if (parentTree == null) return null;
		
		String label = parentTree.getLabel();
		int indexOfMethodName = label.indexOf("MethodName:");
		int indexOrPara = label.indexOf("@@Argus:");
		
		// Match parameter data types.
		String paraStr = label.substring(indexOrPara + 8);
		if (paraStr.startsWith("null")) {
			paraStr = null;
		} else {
			int indexExp = paraStr.indexOf("@@Exp:");
			if (indexExp > 0) paraStr = paraStr.substring(0, indexExp);
		}
		
		// Read return type.
		String returnType = label.substring(label.indexOf("@@") + 2, indexOfMethodName - 2);
		int index = returnType.indexOf("@@tp:");
		if (index > 0) returnType = returnType.substring(0, index - 2);
		
		returnType = readType(returnType);

		return returnType;
	}
	
	/**
	 * UPD MethodInvocation
	 * ---UPD SimpleName@@MethodName
	 * ------DEL/INS/UPD SimpleName: variable parameter.
	 * 
	 * @author kui.liu
	 *
	 */
	class ModifyMethodVarArgument {
		public void generatePatches(ITree suspMethodInvocation) {
			varTypesMap.clear();
			allVarNamesList.clear();
			allVarNamesMap = readAllVariableNames(suspCodeAst, varTypesMap, allVarNamesList);
			
			List<ITree> children = suspMethodInvocation.getChildren();
			if (children.isEmpty()) {// Zero-parameter: method().
				insertVarArgument(suspMethodInvocation, "");
				return;
			}
			
			int methodInvocStartPos = suspMethodInvocation.getPos();
			String methodInvCodeStr = getSubSuspiciouCodeStr(methodInvocStartPos, methodInvocStartPos + suspMethodInvocation.getLength());
			// exp.method(...).
			suspMethodInvocation = children.get(children.size() - 1);
			String varReference = methodInvCodeStr.substring(0, suspMethodInvocation.getPos() - methodInvocStartPos);
			if (varReference.endsWith(".")) varReference = varReference.substring(0, varReference.length() - 1);
			
			List<ITree> parameters = suspMethodInvocation.getChildren();
			if (parameters.isEmpty() && suspMethodInvocation.getLabel().contains("MethodName")) {// Zero-parameter: exp.method().
				insertVarArgument(suspMethodInvocation, varReference);
				return;
			}
			
			List<String> parameterVars = readParameterVariables(parameters);
			for (int index = 0, size = parameters.size(); index < size; index ++) {
				ITree parameter = parameters.get(index);
				int parameterStartPos = parameter.getPos();
				int parameterEndPos = parameterStartPos + parameter.getLength();
				int parameterType = parameter.getType();
				if (Checker.isSimpleName(parameterType)) {
					String codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, parameterStartPos);
					String codePart2 = getSubSuspiciouCodeStr(parameterEndPos, suspCodeEndPos);
					
					// update it.
					for (String var : allVarNamesList) {
						if (parameterVars.contains(var) || var.equals(varReference) || var.endsWith("." + varReference)) continue;
						String fixedCodeStr1 = codePart1 + var + codePart2;
						generatePatch(fixedCodeStr1);
					}
					
					// delete it.
					String fixedCodeStr1;
					if (codePart2.startsWith(",")) {
						fixedCodeStr1 = codePart1 + codePart2.substring(1);
					} else if (codePart1.endsWith(",")) {
						fixedCodeStr1 = codePart1.substring(0, codePart1.length() - 1) + codePart2;
					} else {
						fixedCodeStr1 = codePart1 + codePart2;
					}
					generatePatch(fixedCodeStr1);
				}
				
				// insert a new variable.
				String codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, parameterStartPos);
				String codePart2 = getSubSuspiciouCodeStr(parameterStartPos, suspCodeEndPos);
				for (String var : allVarNamesList) {
					if (parameterVars.contains(var) || var.equals(varReference) || var.endsWith("." + varReference)) continue;
					String fixedCodeStr1 = codePart1 + var + ", " + codePart2;
					generatePatch(fixedCodeStr1);
				}
				if (index == size - 1) {
					codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, parameterEndPos);
					codePart2 = getSubSuspiciouCodeStr(parameterEndPos, suspCodeEndPos);
					for (String var : allVarNamesList) {
						if (parameterVars.contains(var) || var.equals(varReference) || var.endsWith("." + varReference)) continue;
						String fixedCodeStr1 = codePart1 + ", " + var + codePart2;
						generatePatch(fixedCodeStr1);
					}
				}
			}
		}
		
		private List<String> readParameterVariables(List<ITree> parameters) {
			List<String> parameterVars = new ArrayList<>();
			for (ITree parameter : parameters) {
				if (Checker.isSimpleName(parameter.getType()))
					parameterVars.add(parameter.getLabel());
			}
			return parameterVars;
		}

		private void insertVarArgument(ITree suspMethodInvocation, String varReference) {
			String label = suspMethodInvocation.getLabel();
			String methodName = "";
			try {
				methodName = label.substring(11);
				int index = methodName.indexOf(":");
				methodName = methodName.substring(0, index);
			} catch (Exception e) {
				e.printStackTrace();
				System.err.println(methodName + " = " + suspMethodInvocation.toShortString());
				return;
			}
			
			int expStartPos = suspMethodInvocation.getPos() + methodName.length();
			String codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, expStartPos);
			String codePart2 = getSubSuspiciouCodeStr(expStartPos, suspCodeEndPos).trim().substring(2);
			
			// Insert a variable as a parameter.
			for (String var : allVarNamesList) {
				if (varReference.equals(var) || var.endsWith("." + varReference)) continue;
				String fixedCodeStr1 = codePart1 + "(" + var + ")" + codePart2;
				generatePatch(fixedCodeStr1);
			}
		}

	}

	/**
	 * UPD MethodInvocation
	 * ---UPD SimpleName@@MethodName
	 * ------DEL SimpleName
	 * ------INS MethodInvocation
	 * ---------INS SimpleName@@Name
	 * ---------INS SimpleName@@MethodName
	 * 
	 * @author kui.liu
	 *
	 */
	class ModifyMethodVarArgument2MethodInv {
		public void generatePatches(ITree suspMethodInvocation) {
			List<ITree> children = suspMethodInvocation.getChildren();
			if (children.isEmpty()) return; // Zero-parameter: method().
			
			// exp.method(...).
			suspMethodInvocation = children.get(children.size() - 1);
			List<ITree> parameters = suspMethodInvocation.getChildren();
			if (parameters.isEmpty()) return; // Zero-parameter: exp.method().
			
			readLocalData();
			
			for (int index = 0, size = parameters.size(); index < size; index ++) {
				ITree parameter = parameters.get(index);
				int parameterStartPos = parameter.getPos();
				int parameterEndPos = parameterStartPos + parameter.getLength();
				int parameterType = parameter.getType();
				if (Checker.isSimpleName(parameterType)) {
					String codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, parameterStartPos);
					String codePart2 = getSubSuspiciouCodeStr(parameterEndPos, suspCodeEndPos);
//					String varName = parameter.getLabel();
					
//					for (ProjectLiteral pl : dataList1) {
//						String[] methodInvocations = pl.methodInvocation;
//						for (String var : methodInvocations) {
//							String fixedCodeStr1 = codePart1 + var + codePart2;
//							generatePatch(fixedCodeStr1);
//						}
//					}
//					for (ProjectLiteral pl : dataList2) {
//						String[] methodInvocations = pl.methodInvocation;
//						for (String var : methodInvocations) {
//							String fixedCodeStr1 = codePart1 + var + codePart2;
//							generatePatch(fixedCodeStr1);
//						}
//					}
					
					// Get the data type of the variable.
					//TODO MethodInvocations.
					// Match method invocation expressions of which return type is the data type.
					// Another way
					/*
					 * Get all variables and their related method-invocations.
					 */
				}
			}
		}
	}

	/**
	 * UPD MethodInvocation
	 * ---UPD SimpleName@@MethodName
	 * -----UPD QualifiedName@@Calendar.HOUR
	 * --------UPD SimpleName@@HOUR
	 * 
	 * @author kui.liu
	 *
	 */
	class ModifyMethodQualifiedVarArgument {
		public void generatePatches(ITree suspMethodInvocation) {
			List<ITree> children = suspMethodInvocation.getChildren();
			if (children.isEmpty()) {// Zero-parameter: method().
				return;
			}
			
			// exp.method(...).
			suspMethodInvocation = children.get(children.size() - 1);
			List<ITree> parameters = suspMethodInvocation.getChildren();
			if (parameters.isEmpty()) {// Zero-parameter: exp.method().
				return;
			}
			
			if (classDeclarationAst == null) {
				readClassDeclaration(suspCodeAst);
			}
			if (className == null) {
				readClassName(suspCodeAst);
				readPackageName();
			}
			String codePath = packageName + "." + className;
			
			List<ProjectLiteral> dataList1 = selectData(literals, codePath);// JDK8: literals.stream().filter(x -> x.codePath.equals(codePath)).collect(Collectors.toList());
			List<ProjectLiteral> dataList2 = new ArrayList<>();
			dataList2.addAll(literals);
			dataList2.removeAll(dataList1);// JDK8: literals.stream().filter(x -> !x.codePath.equals(codePath)).collect(Collectors.toList());
			
			for (int index = 0, size = parameters.size(); index < size; index ++) {
				ITree parameter = parameters.get(index);
				int parameterStartPos = parameter.getPos();
				int parameterEndPos = parameterStartPos + parameter.getLength();
				int parameterType = parameter.getType();
				if (Checker.isQualifiedName(parameterType)) {
					String codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, parameterStartPos);
					String codePart2 = getSubSuspiciouCodeStr(parameterEndPos, suspCodeEndPos);
					String varName = parameter.getLabel();
					String varPart1 = varName.substring(0, varName.indexOf(".") + 1);
					// update it.
					for (ProjectLiteral pl : dataList1) {
						String[] qualifiedNames = pl.qualifiedNames;
						for (String qualifiedName : qualifiedNames) {
							if (qualifiedName.startsWith(varPart1) && !qualifiedName.equals(varName)) {
								String fixedCodeStr1 = codePart1 + qualifiedName + codePart2;
								generatePatch(fixedCodeStr1);
							}
						}
					}
					for (ProjectLiteral pl : dataList2) {
						String[] qualifiedNames = pl.qualifiedNames;
						for (String qualifiedName : qualifiedNames) {
							if (qualifiedName.startsWith(varPart1) && !qualifiedName.equals(varName)) {
								String fixedCodeStr1 = codePart1 + qualifiedName + codePart2;
								generatePatch(fixedCodeStr1);
							}
						}
					}
				}
			}
		}
	}
	
	/**
	 * UPD MethodInvocation
	 * ---UPD SimpleName@@MethodName
	 * ------UPD/INS/DEL BooleanLiteral
	 *
	 * @author kui.liu
	 *
	 */
	class ModifyMethodBoolArgument {
		public void generatePatches(ITree suspMethodInvocation) {
			List<ITree> parameters = suspMethodInvocation.getChildren();
			if (parameters.isEmpty()) {
				// insert.
				String label = suspMethodInvocation.getLabel();
				String methodName = label.substring(11, label.lastIndexOf(":"));
				generatePatch( methodName + "(true);");
				generatePatch( methodName + "(false);");
				return;
			}
			
			suspMethodInvocation = parameters.get(parameters.size() - 1);
			parameters = suspMethodInvocation.getChildren();
			
			if (parameters.isEmpty() && suspMethodInvocation.getLabel().contains("MethodName")) {
				String label = suspMethodInvocation.getLabel();
				String methodName = label.substring(11, label.lastIndexOf(":"));
				int expStartPos = suspMethodInvocation.getPos() + methodName.length();
				String codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, expStartPos);
				String codePart2 = getSubSuspiciouCodeStr(expStartPos, suspCodeEndPos).trim().substring(2);
				
				generatePatch( codePart1 + "(true)" + codePart2);
				generatePatch( codePart1 + "(false)" + codePart2);
				return;
			}
			
			for (int index = 0, size = parameters.size(); index < size; index ++) {
				ITree parameter = parameters.get(index);
				if (Checker.isBooleanLiteral(parameter.getType())) {
					int argStartPos = parameter.getPos();
					boolean boolVal = Boolean.valueOf(parameter.getLabel());
					String codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, argStartPos);
					String codePart2;
					
					// update (reverse) the boolean value.
					if (boolVal) {
						codePart2 = "false" + getSubSuspiciouCodeStr(argStartPos + 4, suspCodeEndPos);
					} else {
						codePart2 = "true" + getSubSuspiciouCodeStr(argStartPos + 5, suspCodeEndPos);
					}
					generatePatch(codePart1 + codePart2);
					
					// delete
					int argEndPos;
					if (index == size - 1) {
						argEndPos = argStartPos + parameter.getLength();
						if (index != 0) {
							argStartPos = parameters.get(index - 1).getPos() + 
									parameters.get(index - 1).getLength();
						}
					} else {
						argEndPos = parameters.get(index + 1).getPos();
					}
					codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, argStartPos);
					codePart2 = getSubSuspiciouCodeStr(argEndPos, suspCodeEndPos);
					generatePatch(codePart1 + codePart2);
				}
				
				// insert a boolean parameter.
				int argStartPos = parameter.getPos();
				String codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, argStartPos);
				String codePart2 = getSubSuspiciouCodeStr(argStartPos, suspCodeEndPos);
				generatePatch(codePart1 + "true, " + codePart2);
				generatePatch(codePart1 + "false, " + codePart2);
				if (index == size - 1) {
					int argEndPos = argStartPos + parameter.getLength();
					codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, argEndPos);
					codePart2 = getSubSuspiciouCodeStr(argEndPos, suspCodeEndPos);
					generatePatch(codePart1 + ", true" + codePart2);
					generatePatch(codePart1 + ", false" + codePart2);
				}
			}
		}
	} 
	
	/**
	 * UPD MethodInvocation
	 * ---UPD SimpleName
	 * ------UPD StringLiteral parameter
	 * 
	 * @author kui.liu
	 *
	 */
	class ModifyMethodStringArgument {
		public void generatePatches(ITree suspMethodInvocation) {
			triedPatchCodeList.clear();
			List<ITree> parameters = suspMethodInvocation.getChildren();
			if (parameters.isEmpty()) {
				return;
			}
			
			suspMethodInvocation = parameters.get(parameters.size() - 1);
			parameters = suspMethodInvocation.getChildren();
			
			if (parameters.isEmpty()) {
				return;
			}
			
			if (classDeclarationAst == null) {
				readClassDeclaration(suspCodeAst);
			}
			if (className == null) {
				readClassName(suspCodeAst);
				readPackageName();
			}
			String codePath = packageName + "." + className;
			
			for (int index = 0, size = parameters.size(); index < size; index ++) {
				ITree parameter = parameters.get(index);
				if (Checker.isStringLiteral(parameter.getType())) {
					int argStartPos = parameter.getPos();
					int argEndPos = argStartPos + parameter.getLength();
					String strVal = parameter.getLabel();
					String codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, argStartPos);
					String codePart2 = getSubSuspiciouCodeStr(argEndPos, suspCodeEndPos);
					
					List<ProjectLiteral> subLiteralList = selectData(literals, codePath);// JDK8: literals.stream().filter(x -> x.codePath.equals(codePath)).collect(Collectors.toList());
					updateStringLiteral(subLiteralList, strVal, codePart1, codePart2);
					List<ProjectLiteral> subLiteralList2 = new ArrayList<>();
					subLiteralList2.addAll(literals);
					subLiteralList2.removeAll(subLiteralList);// JDK8: literals.stream().filter(x -> !x.codePath.equals(codePath)).collect(Collectors.toList());
					updateStringLiteral(subLiteralList2, strVal, codePart1, codePart2);
				}
			}
		}
	}
	
	List<String> triedPatchCodeList = new ArrayList<>();
	
	private void updateStringLiteral(List<ProjectLiteral> subLiteralList, String stringLiteralStr, String codePart1,
			String codePart2) {
		for (ProjectLiteral literal : subLiteralList) {
			String[] allStringLiterals = literal.stringLiterals;
			for (String str : allStringLiterals) {
				if (str.equals(stringLiteralStr)) continue;
				String fixedCodeStr1 = codePart1 + str + codePart2;
				if (!triedPatchCodeList.contains(fixedCodeStr1)) {
					generatePatch(fixedCodeStr1);
					triedPatchCodeList.add(fixedCodeStr1);
				}
			}
		}
	}
	
	/**
	 * UPD MethodInvocation
	 * ---UPD SimpleName(Method name)
	 * ------UPD InfixExpression
	 * ---------UPD StringLiteral
	 * 
	 * @author kui.liu
	 *
	 */
	class ModifyMethodInfixStringArgument {
		public void generatePatches(ITree suspMethodInvocation) {
			triedPatchCodeList.clear();
			List<ITree> parameters = suspMethodInvocation.getChildren();
			if (parameters.isEmpty()) {
				return;
			}
			
			suspMethodInvocation = parameters.get(parameters.size() - 1);
			parameters = suspMethodInvocation.getChildren();
			
			if (parameters.isEmpty()) {
				return;
			}
			
			if (classDeclarationAst == null) {
				readClassDeclaration(suspCodeAst);
			}
			if (className == null) {
				readClassName(suspCodeAst);
				readPackageName();
			}
			String codePath = packageName + "." + className;
			
			for (int index = 0, size = parameters.size(); index < size; index ++) {
				ITree parameter = parameters.get(index);
				if (Checker.isInfixExpression(parameter.getType())) {
					List<ITree> subExps = parameter.getChildren();
					ITree firstSubExp = subExps.get(0);
					if (Checker.isStringLiteral(firstSubExp.getType())) {
						int argStartPos = firstSubExp.getPos();
						int argEndPos = argStartPos + firstSubExp.getLength();
						String strVal = firstSubExp.getLabel();
						String codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, argStartPos);
						String codePart2 = getSubSuspiciouCodeStr(argEndPos, suspCodeEndPos);
						
						List<ProjectLiteral> subLiteralList = selectData(literals, codePath);// JDK8: literals.stream().filter(x -> x.codePath.equals(codePath)).collect(Collectors.toList());
						List<ProjectLiteral> subLiteralList2 = new ArrayList<>();
						subLiteralList2.addAll(literals);
						subLiteralList2.removeAll(subLiteralList);// JDK8: literals.stream().filter(x -> !x.codePath.equals(codePath)).collect(Collectors.toList());
						
						updateStringLiteral(subLiteralList, strVal, codePart1, codePart2);
						updateStringLiteral(subLiteralList2, strVal, codePart1, codePart2);
					}
					
					for (int i = 2, size2 = subExps.size(); i < size2; i ++) {
						ITree subExp = subExps.get(i);
						if (Checker.isStringLiteral(subExp.getType())) {
							int argStartPos = subExp.getPos();
							int argEndPos = argStartPos + subExp.getLength();
							String strVal = subExp.getLabel();
							String codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, argStartPos);
							String codePart2 = getSubSuspiciouCodeStr(argEndPos, suspCodeEndPos);
							
							List<ProjectLiteral> subLiteralList = selectData(literals, codePath);// JDK8: literals.stream().filter(x -> x.codePath.equals(codePath)).collect(Collectors.toList());
							List<ProjectLiteral> subLiteralList2 = new ArrayList<>();
							subLiteralList2.addAll(literals);
							subLiteralList2.removeAll(subLiteralList);// JDK8: literals.stream().filter(x -> !x.codePath.equals(codePath)).collect(Collectors.toList());
							
							updateStringLiteral(subLiteralList, strVal, codePart1, codePart2);
							updateStringLiteral(subLiteralList, strVal, codePart1, codePart2);
						}
					}
				}
			}
		}
	}

	/**
	 * UPD MethodInvocation
	 * ---UPD SimpleName@@MethodName
	 * ------UPD NumberLiteral
	 * 
	 * @author kui.liu
	 *
	 */
	class ModifyMethodNumberArgument {

		List<String> triedPatchCodeList = new ArrayList<>();
		
		public void generatePatches(ITree suspMethodInvocation) {
			List<ITree> parameters = suspMethodInvocation.getChildren();
			if (parameters.isEmpty()) {
				return;
			}
			
			suspMethodInvocation = parameters.get(parameters.size() - 1);
			parameters = suspMethodInvocation.getChildren();
			
			if (parameters.isEmpty()) {
				return;
			}
			
			if (classDeclarationAst == null) {
				readClassDeclaration(getSuspiciousCodeTree());
			}
			if (className == null) {
				readClassName(getSuspiciousCodeTree());
				readPackageName();
			}
			
			String codePath = packageName + "." + className;
			
			for (int index = 0, size = parameters.size(); index < size; index ++) {
				ITree parameter = parameters.get(index);
				if (Checker.isNumberLiteral(parameter.getType())) {
					int argStartPos = parameter.getPos();
					int argEndPos = argStartPos + parameter.getLength();
					String numVal = parameter.getLabel();
					String codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, argStartPos);
					String codePart2 = getSubSuspiciouCodeStr(argEndPos, suspCodeEndPos);

					List<ProjectLiteral> subLiteralList = selectData(literals, codePath);// JDK8: literals.stream().filter(x -> x.codePath.equals(codePath)).collect(Collectors.toList());
					List<ProjectLiteral> subLiteralList2 = new ArrayList<>();
					subLiteralList2.addAll(literals);
					subLiteralList2.removeAll(subLiteralList);// JDK8: literals.stream().filter(x -> !x.codePath.equals(codePath)).collect(Collectors.toList());
					
					updateNumberLiteral(subLiteralList, numVal, codePart1, codePart2);
					updateNumberLiteral(subLiteralList2, numVal, codePart1, codePart2);
				}
			}
		}

		private void updateNumberLiteral(List<ProjectLiteral> literalList, String numLiteralStr, String codePart1,
				String codePart2) {
			for (ProjectLiteral literal : literalList) {
				String[] allNumberLiterals = literal.numberLiterals;
				for (String num : allNumberLiterals) {
					if (num.equals(numLiteralStr)) continue;
					String fixedCodeStr1 = codePart1 + num + codePart2;
					if (triedPatchCodeList.contains(fixedCodeStr1)) {
						generatePatch(fixedCodeStr1);
						triedPatchCodeList.add(fixedCodeStr1);
					}
				}
			}
		}
	}

	/**
	 * UPD MethodInvocation
	 * ---UPD SimpleName(method name)
	 * @author kui.liu
	 *
	 */
	class ModifyMethodName {
		public void generatePatches(ITree suspMethodInvocation, String returnType) {
//			returnType = "";// =ReturnType=, =Void=/"", boolean
			List<ITree> parameters = suspMethodInvocation.getChildren();
			if (parameters.isEmpty()) {
				suspMethodInvocations.put(suspMethodInvocation, 1);
			} else {
				ITree methodNameNode = parameters.get(parameters.size() - 1);
				if (methodNameNode.getLabel().contains("MethodName")){
					suspMethodInvocations.put(suspMethodInvocation, 2);
					String methodName = methodNameNode.getLabel().substring(11);
					methodName = methodName.substring(0, methodName.indexOf(":"));
					int startPos = methodNameNode.getPos();
					int endPos = startPos + methodName.length();
					String codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, startPos);
					String codePart2 = getSubSuspiciouCodeStr(endPos, suspCodeEndPos);
					String fixedCodeStr1 = null;
					/*
					*  hashCode --> toHashCode,
					*  toString --> toStringBinary,
					*  getName --> getShortName,
					*  indexOf --> lastIndexOf.
					*/
					if ("indexOf".equals(methodName)) {
						fixedCodeStr1 = codePart1 + "lastIndexOf" + codePart2;
	//				} else if ("lastIndexOf".equals(methodName)) {
	//					fixedCodeStr1 = codePart1 + "indexOf" + codePart2;
					} else if ("hashCode".equals(methodName)) {
						fixedCodeStr1 = codePart1 + "toHashCode" + codePart2;
	//				} else if ("toHashCode".equals(methodName)) {
	//					fixedCodeStr1 = codePart1 + "hashCode" + codePart2;
					} else if ("toString".equals(methodName)) {
						fixedCodeStr1 = codePart1 + "toStringBinary" + codePart2;
	//				} else if ("toStringBinary".equals(methodName)) {
	//					fixedCodeStr1 = codePart1 + "toString" + codePart2;
					} else if ("getName".equals(methodName)) {
						fixedCodeStr1 = codePart1 + "getShortName" + codePart2;
	//				} else if ("getShortName".equals(methodName)) {
	//					fixedCodeStr1 = codePart1 + "getName" + codePart2;
					}
					if (fixedCodeStr1 != null) {
						generatePatch(fixedCodeStr1);
						return;
					}
				}
			}
			
			List<MethodInvocationExpression> suspMethodInvList = identifySuspiciousMethodInvocations(returnType);
		
			for (MethodInvocationExpression suspM : suspMethodInvList) {
				ITree methodNameNode = suspM.getCodeAst();
				String methodName = suspM.getMethodName();
				int startPos = methodNameNode.getPos();
				int endPos = startPos + methodName.length();
				String codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, startPos);
				String codePart2 = getSubSuspiciouCodeStr(endPos, suspCodeEndPos);
				
				Map<String, List<String>> couldBeReplacedMethods = suspM.getCouldBeReplacedMethods();
				if (couldBeReplacedMethods == null || couldBeReplacedMethods.isEmpty()) continue;
				List<String> possibleNames = couldBeReplacedMethods.get(returnType);
				if (possibleNames == null || possibleNames.isEmpty()) {
					List<String> triedMethodNames = new ArrayList<>();
					for (Map.Entry<String, List<String>> entry : couldBeReplacedMethods.entrySet()) {
						possibleNames = entry.getValue();
						for (String possibleName : possibleNames) {
							if (triedMethodNames.contains(possibleName)) continue;
							triedMethodNames.add(possibleName);
							String fixedCodeStr1 = codePart1 + possibleName + codePart2;
							generatePatch(fixedCodeStr1);
						}
					}
				} else {
					List<String> triedMethodNames = new ArrayList<>();
					for (String possibleName : possibleNames) {
						if (triedMethodNames.contains(possibleName)) continue;
						triedMethodNames.add(possibleName);
						String fixedCodeStr1 = codePart1 + possibleName + codePart2;
						generatePatch(fixedCodeStr1);
					}
				}
			}
		}
	}
	
	/**
	 * UPD MethodInvocation
	 * ---UPD MethodInvocation(method name)
	 * e.g., exp.method1().method2() --> exp.method().method2().
	 * 
	 * @author kui.liu
	 *
	 */
	class MethodMidMethodName{
		public void generatePatches(ITree suspMethodInvocation) {
			List<ITree> children = suspMethodInvocation.getChildren();
			if (children.isEmpty()) return;
			suspMethodInvocations.clear();
			for (int index = 0, size = children.size() - 1; index < size; index ++) {
				ITree tree = children.get(index);
				if (Checker.isMethodDeclaration(tree.getType())) {
					suspMethodInvocations.put(suspMethodInvocation, 3);
				}
			}
			
			List<MethodInvocationExpression> suspMethodInvList = identifySuspiciousMethodInvocations("");
			
			for (MethodInvocationExpression suspM : suspMethodInvList) {
				ITree methodNameNode = suspM.getCodeAst();
				String methodName = suspM.getMethodName();
				int startPos = methodNameNode.getPos();
				int endPos = startPos + methodName.length();
				String codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, startPos);
				String codePart2 = getSubSuspiciouCodeStr(endPos, suspCodeEndPos);
				
				Map<String, List<String>> couldBeReplacedMethods = suspM.getCouldBeReplacedMethods();
				if (couldBeReplacedMethods == null || couldBeReplacedMethods.isEmpty()) continue;
				
				List<String> triedMethodNames = new ArrayList<>();
				for (Map.Entry<String, List<String>> entry : couldBeReplacedMethods.entrySet()) {
					List<String> possibleNames = entry.getValue();
					for (String possibleName : possibleNames) {
						if (triedMethodNames.contains(possibleName)) continue;
						triedMethodNames.add(possibleName);
						String fixedCodeStr1 = codePart1 + possibleName + codePart2;
						generatePatch(fixedCodeStr1);
					}
				}
			}
		}
	}

	/**
	 * UPD MethodInvocation
	 * ---DEL SimpleName@@Name
	 * ---INS MethodInvocatio
	 * e.g., var.method1() --> method().method1().
	 * 
	 * @author kui.liu
	 *
	 */
	class ModifyMethodVarReference2Method {
		public void generatePatches(ITree suspMethodInvocation) {
			List<ITree> parameters = suspMethodInvocation.getChildren();
			if (parameters.isEmpty()) return;
			ITree tree = parameters.get(0);
			int type = tree.getType();
			
			if (classDeclarationAst == null) {
				readClassDeclaration(suspCodeAst);
			}
			if (className == null) {
				readClassName(suspCodeAst);
				readPackageName();
			}
			String codePath = packageName + "." + className;
			
			List<ProjectLiteral> dataList1 = selectData(literals, codePath);// JDK8: literals.stream().filter(x -> x.codePath.equals(codePath)).collect(Collectors.toList());
			List<ProjectLiteral> dataList2 = new ArrayList<>();
			if (literals != null) {
				dataList2.addAll(literals);
				dataList2.removeAll(dataList1);// JDK8: literals.stream().filter(x -> !x.codePath.equals(codePath)).collect(Collectors.toList());
			}
			
			List<String> methodInvocationLists = readLocalMethodInvocations(suspCodeAst);
			
			if (Checker.isSimpleName(type) || Checker.isQualifiedName(type)) {
				int startPos = tree.getPos();
				int endPos = startPos + tree.getLength();
				String codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, startPos);
				String codePart2 = getSubSuspiciouCodeStr(endPos, suspCodeEndPos);
				
				for (String mi : methodInvocationLists) {
					String fixedCodeStr1 = codePart1 + mi + "()" + codePart2;
					generatePatch(fixedCodeStr1);
				}
				
				for (ProjectLiteral pl : dataList1) {
					String[] methodInvocations = pl.methodInvocation;
					for (String mi : methodInvocations) {
						String fixedCodeStr1 = codePart1 + mi + codePart2;
						generatePatch(fixedCodeStr1);
					}
				}
				
				for (ProjectLiteral pl : dataList2) {
					String[] methodInvocations = pl.methodInvocation;
					for (String mi : methodInvocations) {
						String fixedCodeStr1 = codePart1 + mi + codePart2;
						generatePatch(fixedCodeStr1);
					}
				}
				// Get the data type of the variable.
				//TODO MethodInvocations.
				// Match method invocation expressions of which return type is the data type.
//				for (String var : matchedInvocations) {
//					if (varName.equals(var)) continue;
//					String fixedCodeStr1 = codePart1 + var + codePart2;
//					generatePatch(fixedCodeStr1);
//				}
				// Another way
				/*
				 * Get all variables and their related method-invocations.
				 */
			}
		}
	}
	
	/**
	 * UPD MethodInvocation
	 * ---UPD SimpleName@@Name
	 * e.g., var1.method1() --> var2.method1().
	 * 
	 * @author kui.liu
	 *
	 */
	class ModifyMethodVarReference2VarRef {
		public void generatePatches(ITree suspMethodInvocation) {
			varTypesMap.clear();
			allVarNamesList.clear();
			allVarNamesMap = readAllVariableNames(suspCodeAst, varTypesMap, allVarNamesList);
			
			List<ITree> parameters = suspMethodInvocation.getChildren();
			if (parameters.isEmpty()) return;
			ITree tree = parameters.get(0);
			int type = tree.getType();
			
			if (classDeclarationAst == null) {
				readClassDeclaration(suspCodeAst);
			}
			if (className == null) {
				readClassName(suspCodeAst);
				readPackageName();
			}
			
			
			if (Checker.isSimpleName(type) || Checker.isQualifiedName(type)) {
				int startPos = tree.getPos();
				int endPos = startPos + tree.getLength();
				String codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, startPos);
				String codePart2 = getSubSuspiciouCodeStr(endPos, suspCodeEndPos);
				String buggyVar = tree.getLabel().trim();
				buggyVar = buggyVar.substring(buggyVar.indexOf(":") + 1);
				
				// update it.
				for (String var : allVarNamesList) {
					if (buggyVar.equals(var)) continue;
					String fixedCodeStr1 = codePart1 + var + codePart2;
					generatePatch(fixedCodeStr1);
				}
			}
		}
	}

	public List<String> readLocalMethodInvocations(ITree suspCodeTree) {
		ITree parent = suspCodeTree.getParent();
		while (true) {
			if (Checker.isTypeDeclaration(parent.getType())) break;
			parent = parent.getParent();
			if (parent == null) break;
		}
		
		List<String> methodInvocations = new ArrayList<>();
		if (parent==null) return methodInvocations;
		List<ITree> children = parent.getChildren();
		for (ITree child : children) {
			if (Checker.isMethodDeclaration(child.getType())) {
				String label = child.getLabel();
				label = label.substring(label.indexOf("@@") + 2);
				if (label.startsWith("=CONSTRUCTOR=,") || label.startsWith("void,")) continue;
				label = label.substring(label.indexOf("MethodName:") + 11);
				String methodName = label.substring(0, label.indexOf(","));
				label = label.substring(label.indexOf(",") + 2);
				if (label.startsWith("@@Argus:null")) methodInvocations.add(methodName);
			}
		}
		return methodInvocations;
	}
	
}
