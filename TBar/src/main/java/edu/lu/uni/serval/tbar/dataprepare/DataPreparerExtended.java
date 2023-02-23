package edu.lu.uni.serval.tbar.dataprepare;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import edu.lu.uni.serval.tbar.utils.FileHelper;
import edu.lu.uni.serval.tbar.utils.JavaLibrary;
import edu.lu.uni.serval.tbar.utils.PathUtilsExtended;

public class DataPreparerExtended extends DataPreparer {

	private static Logger log = LoggerFactory.getLogger(DataPreparerExtended.class);

    public DataPreparerExtended(String buggyProject) {
        super(buggyProject);
    }

    @Override
    protected void loadPaths(String buggyProject) {
		String projectDir = buggyProjectParentPath;
		List<String> paths = PathUtilsExtended.getSrcPath(buggyProject);
		classPath = projectDir + buggyProject + paths.get(0);
		testClassPath = projectDir + buggyProject + paths.get(1);
		srcPath = projectDir + buggyProject + paths.get(2);
		testSrcPath = projectDir + buggyProject + paths.get(3);

        log.info("ClassPath: " + classPath);
        log.info("TestClassPath: " + testClassPath);
        log.info("SourcePath: " + srcPath);
        log.info("TestSourcePath: " + testSrcPath);

		List<File> libPackages = new ArrayList<>();
		if (new File(projectDir + buggyProject + "/lib/").exists()) {
			libPackages.addAll(FileHelper.getAllFiles(projectDir + buggyProject + "/lib/", ".jar"));
		}
		if (new File(projectDir + buggyProject + "/build/lib/").exists()) {
			libPackages.addAll(FileHelper.getAllFiles(projectDir + buggyProject + "/build/lib/", ".jar"));
		}
		for (File libPackage : libPackages) {
			libPaths.add(libPackage.getAbsolutePath());
		}
	}

    @Override
    protected void loadClassPaths() {
		classPaths = JavaLibrary.classPathFrom(testClassPath);
		classPaths = JavaLibrary.extendClassPathWith(classPath, classPaths);
		if (libPaths != null) {
			for (String lpath : libPaths) {
				classPaths = JavaLibrary.extendClassPathWith(lpath, classPaths);
			}
		}
        log.info("ClassPaths: " + classPaths);
	}

}
