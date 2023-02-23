package edu.uni.lu.serval.fixminer.fixtemplate;

import edu.lu.uni.serval.templates.AlterMethodInvocation;

/**
 * 
 * @author kui.liu
 *
 */
public class ModifyIfVariable extends AlterMethodInvocation {

	@Override
	public void generatePatches() {
		ModifyVariable mv = new ModifyVariable();
		mv.setLiterals(this.literals);
		mv.setSuspiciousCodeStr(this.getSuspiciousCodeStr());
		mv.setSuspiciousCodeTree(this.getSuspiciousCodeTree());
		mv.setSourceCodePath(this.sourceCodePath);
		mv.setSuspJavaFileCode(this.getSuspJavaFileCode());
		mv.generatePatches();
		this.getPatches().addAll(mv.getPatches());
	}

}
