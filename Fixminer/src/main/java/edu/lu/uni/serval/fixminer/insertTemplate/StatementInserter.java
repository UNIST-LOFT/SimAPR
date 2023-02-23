package edu.lu.uni.serval.fixminer.insertTemplate;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import edu.lu.uni.serval.jdt.tree.ITree;
import edu.lu.uni.serval.templates.AlterMethodInvocation;
import edu.lu.uni.serval.utils.Checker;

/**
 * 
 * @author kui.liu
 *
 */
public class StatementInserter extends AlterMethodInvocation {
	
	/*
	 * INS ExpressionStatement
	 * ---INS MethodInvocation
	 * ------INS SimpleName@MethodName
	 * ------(INS SimpleName@Variable) 
	 */

	@Override
	public void generatePatches() {
		ITree suspCodeTree = this.getSuspiciousCodeTree();
		if (Checker.isBreakStatement(suspCodeTree.getType()) || Checker.isContinueStatement(suspCodeTree.getType())) return;
		
		List<ITree> variables = identifyVariables(suspCodeTree);
		if (variables.isEmpty()) return;
		
		allVarNamesMap = readAllVariableNames(suspCodeTree, varTypesMap, allVarNamesList);
		
		
		// Insert a method invocation as a complete statement.
		ITree parent = suspCodeTree.getParent();
		while (true) {
			if (Checker.isTypeDeclaration(parent.getType())) break;
			parent = parent.getParent();
			if (parent == null) return;
		}
		
		List<String> types = new ArrayList<>();
		Map<String, List<String>> varMaps = new HashMap<>();
		for (int index = variables.size() - 1; index >= 0; index --) {
			ITree varTree = variables.get(index);
			String var = varTree.getLabel();
			String varType = this.varTypesMap.get(var);
			if (varType != null) {
				types.add(0, varType);
				List<String> vars = varMaps.get(varType);
				if (vars == null) {
					vars = new ArrayList<>();
					varMaps.put(varType, vars);
				}
				vars.add(var);
			}
		}
		
		List<Method> methods = readMethods(getSuspiciousCodeTree());
		for (Method method : methods) {
			if (!method.getReturnType().equals("void")) continue; // 
			List<String> parameterTypes = method.getParameterTypes();
			if (parameterTypes.isEmpty()) {
				String fixedCodeStr1 = method.getMethodName() + "();";
				this.generatePatch(fixedCodeStr1 + "\n\t" + this.getSuspiciousCodeStr());
				this.generatePatch(this.getSuspiciousCodeStr() + "\n\t" + fixedCodeStr1);
			} else {
				if (types.isEmpty()) continue;
				if (parameterTypes.size() > 1) continue;
				
				boolean isMatched = true;
				List<Map<String, String>> maps = new ArrayList<>();
				for (String parameterType : parameterTypes) {
					List<String> vars = varMaps.get(parameterType);
					if (vars == null) {
						isMatched = false;
						break;
					}
					
					// n * m * l: a set of variable groups used to synthesis patches with this method.
					maps = arrangeVariableGroups(maps, parameterType, vars);
				}
				if (!isMatched) continue;
				
				// Generate patches.
				for (Map<String, String> map : maps) {
					String fixedCodeStr1 = method.getMethodName() + "(";
					Map<String, String> usedVars = new HashMap<>();
					boolean isFailed = false;
					for (String parameterType : parameterTypes) {
						String var = map.get(parameterType);
						String prevParaType = usedVars.get(var);
						if (parameterType.equals(prevParaType)) {
							isFailed = true;
							break;
						}
						if (!fixedCodeStr1.endsWith("(")) {
							fixedCodeStr1 += ",";
						}
						fixedCodeStr1 += var;
					}

					if (isFailed) continue;
					fixedCodeStr1 += ");";
					this.generatePatch(fixedCodeStr1);
					this.generatePatch(fixedCodeStr1 + "\n\t" + this.getSuspiciousCodeStr());
					this.generatePatch(this.getSuspiciousCodeStr() + "\n\t" + fixedCodeStr1);
				}
			}
		}
	}
	
	private List<Map<String, String>> arrangeVariableGroups(List<Map<String, String>> maps, String keyStr, List<String> vars) {
		// n * m * l: a set of variable groups used to synthesis patches by replacing the original variables.
		if (maps.isEmpty()) {
			for (String var : vars) {
				Map<String, String> m = new HashMap<>();
				m.put(keyStr, var);
				maps.add(m);
			}
		} else {
			List<Map<String, String>> maps2 = new ArrayList<>();
			maps2.addAll(maps);
			maps.clear();
			for (String var : vars) {
				List<Map<String, String>> maps3 = new ArrayList<>();
				maps3.addAll(maps2);
				for (Map<String, String> mm : maps3) {
					Map<String, String> m = new HashMap<>();
					m.put(keyStr, var);
					m.putAll(mm);
					maps.add(m);
				}
				maps3.clear();
			}
			maps2.clear();
		}
		return maps;
	}
	
	private List<ITree> identifyVariables(ITree codeAst) {
		List<ITree> variables = new ArrayList<>();
		List<ITree> children = codeAst.getChildren();
		for (ITree child : children) {
			int type = child.getType();
			if (Checker.isMethodInvocation(type)) continue;
			if (Checker.isComplexExpression(type)) 
				variables.addAll(identifyVariables(child));
			else if (Checker.isSimpleName(type)) {
				if (child.getLabel().startsWith("MethodName:")) continue;
				variables.add(child);
			} else if (Checker.isStatement(type) || Checker.isMethodDeclaration(type))
				break;
		}
		return variables;
	}

	private List<Method> readMethods(ITree suspiciousCodeTree) {
		List<Method> methods = new ArrayList<>();
		ITree classDec = suspiciousCodeTree.getParent();
		while (true) {
			if (classDec == null) return null;
			if (Checker.isTypeDeclaration(classDec.getType())) break;
			classDec = classDec.getParent();
		}
		
		if (classDec != null) {
			List<ITree> children = classDec.getChildren();
			for (ITree child : children) {
				if (Checker.isMethodDeclaration(child.getType())) {
					String methodNameInfo = child.getLabel();
					int indexOfMethodName = methodNameInfo.indexOf("MethodName:");
					String methodName = methodNameInfo.substring(indexOfMethodName);
					methodName = methodName.substring(11, methodName.indexOf(", "));
					
					if ("main".equals(methodName)) continue;
					
					boolean isConstructor = false;
					String returnType = readReturnTypeOfMethod(child);
					if ("=CONSTRUCTOR=".equals(returnType)) {// Constructor.
						isConstructor = true;
					}
					
					List<String> parameterTypes = readParameterTypes(methodNameInfo);
					String modifier = readMethodModifier(child);
					Method m = new Method("", modifier, returnType, methodName, parameterTypes, isConstructor);
					methods.add(m);
				}
			}
		}
		
		return methods;
	}
	
	private String readMethodModifier(ITree methodDeclarationTree) {
		List<ITree> children = methodDeclarationTree.getChildren();
		for (ITree child : children) {
			if (Checker.isModifier(child.getType())) {
				if ("public".equals(child.getLabel())) {
					return "public";
				} else if ("protected".equals(child.getLabel())) {
					return "protected";
				} else if ("private".equals(child.getLabel())) {
					return "private";
				}
			} else break;
		}
		return "protected";
	}
	
	private List<String> readParameterTypes(String methodDeclarationLabel) {
		List<String> parameterTypes = new ArrayList<>();
		if (methodDeclarationLabel.endsWith("@@Argus:null")) {
			return parameterTypes;
		} else {
			String argus = methodDeclarationLabel.substring(methodDeclarationLabel.indexOf("@@Argus:") + 8, methodDeclarationLabel.length() - 1).replace(" ", "");
			int expIndex = argus.indexOf("@@Exp:");
			if (expIndex > 0) {
				argus = argus.substring(0, expIndex - 1);
			}
			if (argus.endsWith("@@Argus:null")) {
				return parameterTypes;
			}
			String[] argusArray = argus.split("\\+");
			for (int index = 0, length = argusArray.length; index < length; index = index + 2) {
				String arguType = readType(argusArray[index]);
				parameterTypes.add(arguType);
			}
			
			return parameterTypes;
		}
	}
	
	private String readReturnTypeOfMethod(ITree methodDeclarationTree) {
		String label = methodDeclarationTree.getLabel();
		int indexOfMethodName = label.indexOf("MethodName:");

		// Read return type.
		String returnType = label.substring(label.indexOf("@@") + 2, indexOfMethodName - 2);
		int index = returnType.indexOf("@@tp:");
		if (index > 0) returnType = returnType.substring(0, index - 2);
		return readType(returnType);
	}
	
	protected String readType(String returnType) {
		if (returnType.endsWith("[]")) {
			return readType(returnType.substring(0, returnType.length() - 2)) + "[]";
		}
		
		return readSimpleNameOfDataType(returnType);
	}
	
	private String readSimpleNameOfDataType(String className) {
		int index = className.indexOf("<");
		if (index != -1) {
			if (index == 0) {
				while (index == 0) {
					className = className.substring(className.indexOf(">") + 1).trim();
					index = className.indexOf(">");
				}
				index = className.indexOf("<");
				if (index == -1) index = className.length();
			}
			className = className.substring(0, index);
		}
		index = className.lastIndexOf(".");
		if (index != -1) { // && returnType.startsWith("java.")) {
			className = className.substring(index + 1);
		}

		return className;
	}
	
	class Method {

		private String className;
		private String modifier;
		private String returnType;
		private String methodName;
		private List<String> parameterTypes;
		private boolean isConstructor;
		
		public Method(String className, String modifier, String returnType, String methodName,
				List<String> parameterTypes, boolean isConstructor) {
			super();
			this.className = className;
			this.modifier = modifier;
			this.returnType = returnType;
			this.methodName = methodName;
			this.parameterTypes = parameterTypes;
			this.isConstructor = isConstructor;
		}

		public String getPackageName() {
			return packageName;
		}

		public String getClassName() {
			return className;
		}

		public String getModifier() {
			return modifier;
		}

		public String getReturnType() {
			return returnType;
		}

		public String getMethodName() {
			return methodName;
		}

		public List<String> getParameterTypes() {
			return parameterTypes;
		}

		public boolean isConstructor() {
			return isConstructor;
		}
		
	}
}
