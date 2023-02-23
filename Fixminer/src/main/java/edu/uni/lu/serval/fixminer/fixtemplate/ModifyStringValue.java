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
public class ModifyStringValue extends AlterMethodInvocation {

	/*
	 * Updating StringLiteral Value.
	 * 
	 * Assignment StringLiteral value:
	 * Change StringLiteral Value
	 * UPD ExpressionStatement
	 * ---UPD Assignment
	 * ------UPD StringLiteral
	 * 
	 * UPD ExpressionStatement
	 * ---UPD Assignment
	 * ------UPD InfixExpression
	 * ---------UPD StringLiteral
	 * 
	 * UPD VariableDeclarationStatement
	 * ---UPD VariableDeclarationFragment
	 * ------UPD StringLiteral
	 * 
	 * UPD FieldDeclaration
	 * ---UPD VariableDeclarationFragment
	 * ------UPD StringLiteral
	 * 
	 */

	List<String> triedPatchCodeList = new ArrayList<>();
	
	@Override
	public void generatePatches() {
		if (classDeclarationAst == null) {
			readClassDeclaration(this.getSuspiciousCodeTree());
		}
		if (className == null) {
			readClassName(this.getSuspiciousCodeTree());
			readPackageName();
		}
		
		String codePath = this.packageName + "." + this.className;
		
		List<ITree> suspStringLiteral = identifyAllStringLiteral(this.getSuspiciousCodeTree());
		for (ITree stringLiteral : suspStringLiteral) {
			int startPos = stringLiteral.getPos();
			int endPos = startPos + stringLiteral.getLength();
			String codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, startPos);
			String codePart2 = getSubSuspiciouCodeStr(endPos, suspCodeEndPos);
			String stringLiteralStr = stringLiteral.getLabel();
			
			List<ProjectLiteral> subLiteralList = selectData(literals, codePath);//JDK8: this.literals.stream().filter(x -> x.codePath.equals(codePath)).collect(Collectors.toList());
			updateStringLiteral(subLiteralList, stringLiteralStr, codePart1, codePart2);
			List<ProjectLiteral> subLiteralList2 = new ArrayList<>();
			subLiteralList2.addAll(literals);
			subLiteralList2.removeAll(subLiteralList);//JDK8: = this.literals.stream().filter(x -> !x.codePath.equals(codePath)).collect(Collectors.toList());
			updateStringLiteral(subLiteralList, stringLiteralStr, codePart1, codePart2);
		}
	}
	
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

	private List<ITree> identifyAllStringLiteral(ITree codeAst) {
		List<ITree> suspStringLiteral = new ArrayList<>();
		List<ITree> children = codeAst.getChildren();
		for (ITree child : children) {
			int type = child.getType();
			if (Checker.isComplexExpression(type)) 
				suspStringLiteral.addAll(identifyAllStringLiteral(child));
			else if (Checker.isStringLiteral(type))
				suspStringLiteral.add(child);
			else if (Checker.isStatement(type) || Checker.isMethodDeclaration(type))
				break;
		}
		return suspStringLiteral;
	}
	
}
