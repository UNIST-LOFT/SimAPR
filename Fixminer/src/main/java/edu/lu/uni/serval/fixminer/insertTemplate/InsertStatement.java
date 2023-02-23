package edu.lu.uni.serval.fixminer.insertTemplate;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import edu.lu.uni.serval.templates.FixTemplate;

/**
 * 
 * @author kui.liu
 *
 */
public abstract class InsertStatement extends FixTemplate {

	protected Map<String, String> varTypesMap = new HashMap<>();
	protected List<String> allVarNamesList = new ArrayList<>();
	protected Map<String, List<String>> allVarNamesMap;
	
}
