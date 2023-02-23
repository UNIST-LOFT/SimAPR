package edu.lu.uni.serval.fixminer.insertTemplate;

import java.util.List;

import edu.lu.uni.serval.jdt.tree.ITree;

/**
 * 
 * @author kui.liu
 *
 */
public class InsertIfSizeCheck extends InsertStatement {
 /*
  * INS IfStatement
  * 	INS InfixExp@var != 0 || var > 0
  * 	MOV ExpressionStatement@methodInvocation. containing integer var
  *
  * INS IfStatement@@InfixExpression: size == 0 
  * ---INS ThrowStatement@@ClassInstanceCreation:new IllegalArgumentException("SAAJ SOAP message has no body") 
  *
  */
	
	@Override
	public void generatePatches() {
		ITree suspCodeTree = this.getSuspiciousCodeTree();
		List<String> variables = identifySuspiciousVariables(suspCodeTree);
		varTypesMap.clear();
		allVarNamesList.clear();
		allVarNamesMap = readAllVariableNames(suspCodeTree, varTypesMap, allVarNamesList);
		
		for (String var : variables) {
			String varDataType = varTypesMap.get(var);
			if ("Integer".equals(varDataType) || "int".equals(varDataType) || "long".equalsIgnoreCase(varDataType)) {
				String fixedCodeStr1 = "if (" + var + " == 0) {\n    "
						+ "new IllegalArgumentException(\"\");\n}\n";
				this.generatePatch(suspCodeStartPos, fixedCodeStr1);
				
				fixedCodeStr1 = "if (" + var + " != 0) {\n";
				String fixedCodeStr2 = "    \n}\n";
				int suspCodeEndPos = identifyRelatedStatements(suspCodeTree, var);
				this.generatePatch(suspCodeStartPos, suspCodeEndPos, fixedCodeStr1, fixedCodeStr2);
				
				fixedCodeStr1 = "if (" + var + " > 0) {\n";
				this.generatePatch(suspCodeStartPos, suspCodeEndPos, fixedCodeStr1, fixedCodeStr2);
			}
		}
	}
}
