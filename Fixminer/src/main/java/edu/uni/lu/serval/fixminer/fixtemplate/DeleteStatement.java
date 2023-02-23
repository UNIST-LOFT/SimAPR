package edu.uni.lu.serval.fixminer.fixtemplate;

import edu.lu.uni.serval.templates.FixTemplate;

/**
 * Delete the buggy statement.
 * 
 * @author kui.liu
 *
 */
public class DeleteStatement extends FixTemplate {
	
	/*
	 * DEL Statement.
	 */
	
	public DeleteStatement() {
		
	}
	
	
	@Override
	public void generatePatches() {
		String fixedCodeStr1 = "";// Replace the buggy code with empty string.
		this.generatePatch(fixedCodeStr1);
	}


}
