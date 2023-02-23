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
public class ModifyNumberValue extends AlterMethodInvocation {

	/*
	 * Updating NumberLiteral Value.
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
		
		List<ITree> suspNumberLiteral = identifyAllNumberLiteral(this.getSuspiciousCodeTree());
		for (ITree numLiteral : suspNumberLiteral) {
			int startPos = numLiteral.getPos();
			int endPos = startPos + numLiteral.getLength();
			String codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, startPos);
			String codePart2 = getSubSuspiciouCodeStr(endPos, suspCodeEndPos);
			String numLiteralStr = numLiteral.getLabel();
			
			List<ProjectLiteral> subLiteralList = selectData(literals, codePath);// JDK8: literals.stream().filter(x -> x.codePath.equals(codePath)).collect(Collectors.toList());
			List<ProjectLiteral> subLiteralList2 = new ArrayList<>();
			subLiteralList2.addAll(literals);
			subLiteralList2.removeAll(subLiteralList);// JDK8: literals.stream().filter(x -> !x.codePath.equals(codePath)).collect(Collectors.toList());
			
			updateNumberLiteral(subLiteralList, numLiteralStr, codePart1, codePart2);
			updateNumberLiteral(subLiteralList2, numLiteralStr, codePart1, codePart2);
		}
	}
	
	private void updateNumberLiteral(List<ProjectLiteral> literalList, String numLiteralStr, String codePart1,
			String codePart2) {
		for (ProjectLiteral literal : literalList) {
			String[] allNumberLiterals = literal.numberLiterals;
			for (String num : allNumberLiterals) {
				if (num.equals(numLiteralStr)) continue;
				String fixedCodeStr1 = codePart1 + num + codePart2;
				if (!triedPatchCodeList.contains(fixedCodeStr1)) {
					generatePatch(fixedCodeStr1);
					triedPatchCodeList.add(fixedCodeStr1);
				}
			}
		}
	}

	private List<ITree> identifyAllNumberLiteral(ITree codeAst) {
		List<ITree> suspNumberLiteral = new ArrayList<>();
		List<ITree> children = codeAst.getChildren();
		for (ITree child : children) {
			int type = child.getType();
			if (Checker.isComplexExpression(type)) 
				suspNumberLiteral.addAll(identifyAllNumberLiteral(child));
			else if (Checker.isNumberLiteral(type))
				suspNumberLiteral.add(child);
			else if (Checker.isStatement(type) || Checker.isMethodDeclaration(type))
				break;
		}
		return suspNumberLiteral;
	}
	
}
