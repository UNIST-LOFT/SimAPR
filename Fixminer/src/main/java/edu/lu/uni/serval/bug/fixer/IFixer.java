package edu.lu.uni.serval.bug.fixer;

import java.io.IOException;
import java.util.List;

import edu.lu.uni.serval.bug.fixer.AbstractFixer.SuspCodeNode;
import edu.lu.uni.serval.dataprepare.DataPreparer;
import edu.lu.uni.serval.utils.SuspiciousPosition;

/**
 * Interface fixer.
 * 
 * @author kui.liu
 *
 */
public interface IFixer {

	public List<SuspiciousPosition> readSuspiciousCodeFromFile(String metric, String path, String buggyProject, DataPreparer dp);
	
	public SuspCodeNode parseSuspiciousCode(SuspiciousPosition suspiciousCode);

	public void fixProcess(int maxLocation) throws IOException;
	
}
