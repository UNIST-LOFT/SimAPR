package edu.uni.lu.serval.fixminer.fixtemplate;

import java.util.ArrayList;
import java.util.List;

import edu.lu.uni.serval.jdt.tree.ITree;
import edu.lu.uni.serval.templates.FixTemplate;
import edu.lu.uni.serval.utils.Checker;

/**
 * 
 * @author kui.liu
 *
 */
public class ModifyModifier extends FixTemplate {
	
	/*
	 * UPD MethodDeclaration
	 * ---DEL/INS/UPD Modifier
	 */
	
	private List<String> accessModifiers = new ArrayList<>();
	
	// static, final, abstract, synchronized, transient, volatile
//	private List<String> nonAccessModifiers = new ArrayList<>();
	
	public ModifyModifier() {
		accessModifiers.add("public");
		accessModifiers.add("protected");
		accessModifiers.add("private");
//		nonAccessModifiers.add("static");
//		nonAccessModifiers.add("final");
//		nonAccessModifiers.add("transient");
//		nonAccessModifiers.add("volatile");
	}

	@Override
	public void generatePatches() {
		ITree suspCodeTree = this.getSuspiciousCodeTree();
		List<ITree> children = suspCodeTree.getChildren();
		
		List<String> otherModifiers = new ArrayList<>();
		String accessModifier = "";
		for (ITree child : children) {
			if (Checker.isModifier(child.getType())) {
				String modifierStr = child.getLabel();
				if (this.accessModifiers.contains(modifierStr)) {
					accessModifier = modifierStr;
					if (modifierStr.equals("public")) continue;
					
					int modifierStartPos = child.getPos();
					int modifierEndPos = modifierStartPos + child.getLength();
					String codePart1 = this.getSubSuspiciouCodeStr(this.suspCodeStartPos, modifierStartPos);
					String codePart2 = this.getSubSuspiciouCodeStr(modifierEndPos, this.suspCodeEndPos);
					this.generatePatch(codePart1 + "public" + codePart2);
					
					if ("private".equals(modifierStr)) {
						this.generatePatch(codePart1 + "protected" + codePart2);
					}
					
				} else otherModifiers.add(modifierStr);
			} else {
				if ("".equals(accessModifier)) {
					ITree childTemp = children.get(0);
					int modifierStartPos = childTemp.getPos();
					String codePart1 = this.getSubSuspiciouCodeStr(suspCodeStartPos, modifierStartPos);
					String codePart2 = this.getSubSuspiciouCodeStr(modifierStartPos, suspCodeEndPos);
					String fixedCodeStr1 = codePart1 + "public " + codePart2;
					this.generatePatch(fixedCodeStr1);
				}
				break;
			}
		}
		
		modifyNonAccessModifier(otherModifiers, "static", accessModifier, children.get(0));
		modifyNonAccessModifier(otherModifiers, "final", accessModifier, children.get(0));
		modifyNonAccessModifier(otherModifiers, "transient", accessModifier, children.get(0));
		modifyNonAccessModifier(otherModifiers, "volatile", accessModifier, children.get(0));
	}

	private void modifyNonAccessModifier(List<String> otherModifiers, String modifier, String accessModifier, ITree tree) {
		if (otherModifiers.contains(modifier)) {
			String fixedCodeStr1 = this.getSuspiciousCodeStr().replace(modifier, "");
			this.generatePatch(fixedCodeStr1);
		} else {
			if ("".equals(accessModifier)) {
				int modifierStartPos = tree.getPos();
				String codePart1 = this.getSubSuspiciouCodeStr(suspCodeStartPos, modifierStartPos);
				String codePart2 = this.getSubSuspiciouCodeStr(modifierStartPos, suspCodeEndPos);
				String fixedCodeStr1 = codePart1  + " " + modifier + " " + codePart2;
				this.generatePatch(fixedCodeStr1);
			} else {
				int modifierStartPos = tree.getPos() + tree.getLength();
				String codePart1 = this.getSubSuspiciouCodeStr(suspCodeStartPos, modifierStartPos);
				String codePart2 = this.getSubSuspiciouCodeStr(modifierStartPos, suspCodeEndPos);
				String fixedCodeStr1 = codePart1  + " " + modifier + " " + codePart2;
				this.generatePatch(fixedCodeStr1);
			}
		}
	}

}
