package edu.uni.lu.serval.fixminer.fixtemplate;

import java.util.ArrayList;
import java.util.List;

import edu.lu.uni.serval.fixminer.ProjectLiteral;
import edu.lu.uni.serval.jdt.tree.ITree;
import edu.lu.uni.serval.templates.AlterMethodInvocation;
import edu.lu.uni.serval.utils.Checker;

/**
 * 
 * @author kui.liu
 *
 */
public class ModifyVariable extends AlterMethodInvocation {
	
	private boolean isLocalData = true;

	public ModifyVariable() {
		
	}
	
	public ModifyVariable(boolean isLocalData) {
		this();
		this.isLocalData = isLocalData;
	}
	
	@Override
	public void generatePatches() {
		ITree suspCodeTree = this.getSuspiciousCodeTree();
		
		if (isLocalData) {
			allVarNamesMap = readAllLocalVariableNames(suspCodeTree, varTypesMap, allVarNamesList);
		} else {
			allVarNamesMap = readAllVariableNames(suspCodeTree, varTypesMap, allVarNamesList);
		}
		List<ITree> variables = identifyVariables(suspCodeTree);
		
		readLocalData();
		
		for (ITree var : variables) {
			int startPos = var.getPos();
			int endPos = startPos + var.getLength();
			String codePart1 = this.getSubSuspiciouCodeStr(suspCodeStartPos, startPos);
			String codePart2 = this.getSubSuspiciouCodeStr(endPos, suspCodeEndPos);
			
			String varName = var.getLabel();
			if (varName.startsWith("Name:")) varName = varName.substring(5);
			String dataType = varTypesMap.get(varName);
			if (dataType == null) continue;
			List<String> varList = allVarNamesMap.get(dataType);
			if (varList == null) continue;
			varList.remove(varName);
			
			for (String variable : varList) {
				String fixedCodeStr1 = codePart1 + variable + codePart2;
				this.generatePatch(fixedCodeStr1);
			}
			
			// var --> MethodInvocation, var --> QualifiedName.
			repalceVarName(dataList1, codePart1, codePart2);
			if (!isLocalData)  repalceVarName(dataList2, codePart1, codePart2);
		}
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

	private void repalceVarName(List<ProjectLiteral> dataList, String codePart1, String codePart2) {
		for (ProjectLiteral pl : dataList) {
			String[] qualifiedNames = pl.qualifiedNames;
			for (String qn : qualifiedNames) {
				String fixedCodeStr1 = codePart1 + qn + codePart2;
				generatePatch(fixedCodeStr1);
			}
			String[] methodInvocations = pl.methodInvocation;
			for (String mi : methodInvocations) {
				String fixedCodeStr1 = codePart1 + mi + codePart2;
				generatePatch(fixedCodeStr1);
			}
		}
	}

}
