package edu.lu.uni.serval.fixminer.insertTemplate;

import java.util.List;

import edu.lu.uni.serval.jdt.tree.ITree;

/**
 * 
 * @author kui.liu
 *
 */
public class InsertIfNonNullCheck extends InsertStatement {
	 
	 /*
	  * INS IfStatement@@InfixExpression:var != null 
	  */
	
	public void generatePatches() {
		
		ITree suspCodeTree = this.getSuspiciousCodeTree();
		List<String> variables = identifySuspiciousVariables(suspCodeTree);
		varTypesMap.clear();
		allVarNamesList.clear();
		allVarNamesMap = readAllVariableNames(suspCodeTree, varTypesMap, allVarNamesList);
		
		for (String var : variables) {
			String varDataType = varTypesMap.get(var);
			if ("boolean".equals(varDataType) || "byte".equals(varDataType)
					|| "char".equals(varDataType) || "short".equals(varDataType)
					|| "int".equals(varDataType) || "long".equals(varDataType)
					|| "float".equals(varDataType) || "double".equals(varDataType)) {
				continue;
			}
			
			String fixedCodeStr1 = "if (" + var + " != null) {\n";
			String fixedCodeStr2 = "\n}\n";
			int suspCodeEndPos = identifyRelatedStatements(suspCodeTree, var);
			this.generatePatch(suspCodeStartPos, suspCodeEndPos, fixedCodeStr1, fixedCodeStr2);
		}
	}

}
