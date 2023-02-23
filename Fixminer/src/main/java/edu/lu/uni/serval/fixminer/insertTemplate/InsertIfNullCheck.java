package edu.lu.uni.serval.fixminer.insertTemplate;

import java.util.List;

import edu.lu.uni.serval.jdt.tree.ITree;
import edu.lu.uni.serval.utils.Checker;

/**
 * 
 * @author kui.liu
 *
 */
public class InsertIfNullCheck extends InsertStatement {


	 /*
	  * INS IfStatement@@InfixExpression:var == null 
	  * ---INS InfixExpression@@ctx == null 
	  * ——- INS return null;
	  * ——- INS return;
	  * --- INS ThrowStatement@@ClassInstanceCreation:new IllegalArgumentException("SAAJ SOAP message has no body") 
	  */
	
	@Override
	public void generatePatches() {
		ITree suspCodeTree = this.getSuspiciousCodeTree();
		List<String> variables = identifySuspiciousVariables(suspCodeTree);
		varTypesMap.clear();
		allVarNamesList.clear();
		allVarNamesMap = readAllVariableNames(suspCodeTree, varTypesMap, allVarNamesList);
		
		String returnType = readReturnType(suspCodeTree);
		
		for (String var : variables) {
			String varDataType = varTypesMap.get(var);
			if ("boolean".equals(varDataType) || "byte".equals(varDataType)
					|| "char".equals(varDataType) || "short".equals(varDataType)
					|| "int".equals(varDataType) || "long".equals(varDataType)
					|| "float".equals(varDataType) || "double".equals(varDataType)) {
				continue;
			}
			
			String fixedCodeStr1 = "if (" + var + " == null) {\n    return";
			if ("void".equals(returnType)) {

			} else if ("float".equals(returnType) || "double".equals(returnType)) {
				fixedCodeStr1 += " 0.0";
			} else if ("boolean".equalsIgnoreCase(returnType)) {
				fixedCodeStr1 += " true;\n}\n";
				this.generatePatch(suspCodeStartPos, fixedCodeStr1);
				fixedCodeStr1 = "if (" + var + " == null) {\n    return false";
			} else if ("int".equals(returnType) || "long".equals(returnType)) {
				fixedCodeStr1 += " 0";
			} else {
				fixedCodeStr1 += " null";
			}
			fixedCodeStr1 += ";\n}\n";
			this.generatePatch(suspCodeStartPos, fixedCodeStr1);
			fixedCodeStr1 = "if (" + var + " == null) {\n    throw new IllegalArgumentException(\"Empty variable: \" + " 
			+ var + ");\n}\n";
			this.generatePatch(suspCodeStartPos, fixedCodeStr1);
		}
		
	}

	private String readReturnType(ITree suspCodeAst) {
		// ITree parent = suspCodeAst.getParent();
		ITree parent=suspCodeAst;
		do {
			// Add null checker if susp code is not in method
			if (parent==null) return null;
			if (Checker.isMethodDeclaration(parent.getType())) {
				break;
			}
			parent = parent.getParent();
		} while (true);
		String label = parent.getLabel();
		String returnTypeStr = label.substring(label.indexOf("@@") + 2);
		returnTypeStr = returnTypeStr.substring(0, returnTypeStr.indexOf("MethodName:"));
		int index = returnTypeStr.indexOf("@@tp:");
		if (index > 0) index += 2;
		else index = returnTypeStr.length() - 2;
		returnTypeStr = returnTypeStr.substring(0, index);
		return returnTypeStr;
	}
	
}
