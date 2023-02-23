package edu.uni.lu.serval.fixminer.fixtemplate;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import edu.lu.uni.serval.jdt.tree.ITree;
import edu.lu.uni.serval.templates.AlterMethodInvocation;
import edu.lu.uni.serval.utils.Checker;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyMethodInvocation.ModifyType;

/**
 * Modify the value of boolean literal in a method invocation.
 * 
 * @author kui.liu
 *
 */
public class ModifyBooleanArg extends AlterMethodInvocation {

	/*
	 * MethodInvocation BooleanLiteral Parameter: INS, DEL, UPD
	 * UPD ExpressionStatement/ReturnStatement
	 * ---UPD MethodInvocation
	 * ------UPD SimpleName
	 * ---------UPD/INS/DEL BooleanLiteral
	 */

	@Override
	public void generatePatches() {
		ITree suspCodeAst = this.getSuspiciousCodeTree();
		
		List<ITree> children = suspCodeAst.getChildren();
		if (children.size() != 1) return;
		ITree suspExpTree = children.get(0);
		if (Checker.isMethodInvocation(suspExpTree.getType())) {
			ModifyMethodInvocation mmi = new ModifyMethodInvocation(suspExpTree, ModifyType.BoolArgument);
			mmi.setSuspiciousCodeStr(this.getSuspiciousCodeStr());
			mmi.setSuspiciousCodeTree(this.getSuspiciousCodeTree());
			mmi.setSourceCodePath(this.sourceCodePath);
			mmi.setSuspJavaFileCode(this.getSuspJavaFileCode());
			mmi.setLiterals(this.literals);
			mmi.generatePatches();
			this.getPatches().addAll(mmi.getPatches());
		} else if (Checker.isAssignment(suspExpTree.getType())) {
			ITree varTree = suspExpTree.getChild(0);
			String varName = varTree.getLabel();
			String dataType = this.readVarDataType(suspCodeAst, varName);
			suspExpTree = suspExpTree.getChild(2);
			if (Checker.isMethodInvocation(suspExpTree.getType())) {
				ModifyMethodInvocation mmi = new ModifyMethodInvocation(suspExpTree, ModifyType.BoolArgument);
				mmi.returnTypeStr = dataType == null ? "" : dataType;
				mmi.setSuspiciousCodeStr(this.getSuspiciousCodeStr());
				mmi.setSuspiciousCodeTree(this.getSuspiciousCodeTree());
				mmi.setSourceCodePath(this.sourceCodePath);
				mmi.setSuspJavaFileCode(this.getSuspJavaFileCode());
				mmi.setLiterals(this.literals);
				mmi.generatePatches();
				this.getPatches().addAll(mmi.getPatches());
			} else updateBooleanValue(suspExpTree);
		} else updateBooleanValue(suspExpTree);
	}
	
	private void updateBooleanValue(ITree suspExpTree) {
		if (Checker.isBooleanLiteral(suspExpTree.getType())) {
			int argStartPos = suspExpTree.getPos();
			boolean boolVal = Boolean.valueOf(suspExpTree.getLabel());
			String codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, argStartPos);
			String codePart2;
			
			// update (reverse) the boolean value.
			if (boolVal) {
				codePart2 = "false" + getSubSuspiciouCodeStr(argStartPos + 4, suspCodeEndPos);
			} else {
				codePart2 = "true" + getSubSuspiciouCodeStr(argStartPos + 5, suspCodeEndPos);
			}
			generatePatch(codePart1 + codePart2);
		}
	}

	private String readVarDataType(ITree codeAst, String varName) {
		Map<String, List<String>> varNamesMap = new HashMap<>();
		Map<String, String> varTypesMap = new HashMap<>();
		List<String> allVarNamesList = new ArrayList<>();
		
		while (true) {
			int parentTreeType = codeAst.getType();
			if (Checker.isStatement(parentTreeType)) {// variable
				readVariableDeclaration(codeAst, parentTreeType, varNamesMap, varTypesMap, allVarNamesList);
				if (varTypesMap.containsKey(varName)) return varTypesMap.get(varName);
				varTypesMap.clear();
				
				parentTreeType = codeAst.getParent().getType();
				if (Checker.isStatement(parentTreeType) || Checker.isMethodDeclaration(parentTreeType)) {
					List<ITree> children = codeAst.getParent().getChildren();
					int index = children.indexOf(codeAst) - 1;
					for (; index >= 0; index --) {
						ITree child = children.get(index);
						int childType = child.getType();
						if (!Checker.isStatement(childType)) break;
						readVariableDeclaration(child, childType, varNamesMap, varTypesMap, allVarNamesList);
						if (varTypesMap.containsKey(varName)) return varTypesMap.get(varName);
						varTypesMap.clear();
					}
				}
			} else if (Checker.isMethodDeclaration(parentTreeType)) { // parameter type.
				List<ITree> children = codeAst.getChildren();
				for (ITree child : children) {
					int childType = child.getType();
					if (Checker.isStatement(childType)) break;
					readSingleVariableDeclaration(child, childType, varNamesMap, varTypesMap, allVarNamesList);
					if (varTypesMap.containsKey(varName)) return varTypesMap.get(varName);
					varTypesMap.clear();
				}
			} else if (Checker.isTypeDeclaration(parentTreeType)) {// Field
				List<ITree> children = codeAst.getChildren();
				for (ITree child : children) {
					int childType = child.getType();
					if (Checker.isFieldDeclaration(childType)) {
						List<ITree> subChildren = child.getChildren();
						boolean readVar = false;
						String varType = null;
						for (ITree subChild : subChildren) {
							if (readVar) {
								String fieldName = subChild.getChild(0).getLabel();
								if (fieldName.equals(varName)) return varType;
							} else if (!Checker.isModifier(subChild.getType())) {
								varType = this.readType(subChild.getLabel());
								readVar = true;
							}
						}
					}
				}
			}
			codeAst = codeAst.getParent();
			if (codeAst == null) break;
			if (codeAst.getType() == 15) break; // CompilationUnit
		}
		/*
		 *  TODO: fields in the super class.
		 *  public fields: this.var
		 *  protected fields: var.
		 *  private fields: this.getVar().
		 */
//		readFieldsInSuperClass(varNamesMap, varTypesMap, allVarNamesList);
		return null;
	}

}
