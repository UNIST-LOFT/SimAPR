package anonymous;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import edu.lu.uni.serval.utils.ShellUtils;
import edu.lu.uni.serval.utils.TestUtils;

/**
 * Validate all tests with fixed version.
 * <p>
 *  We don't want to run failed tests that failed reason is not bug.
 *  Validate all tests with fixed version, and return all failed tests in fixed version.
 * </p>
 */
public class TestValidator {
    private String projectParentPath;
    private String projectName;
    private String subject;
    private int version;
    private String d4jPath;

    private static Logger log=LoggerFactory.getLogger(TestValidator.class);

    /**
     * Constructor with parent path, project name and defects4j path.
     * @param projectParentPath parent path of project (e.g. /home/user if project path is /home/user/Math_50)
     * @param projectName project name (e.g. Math_50)
     * @param d4jPath defects4j path
     */
    public TestValidator(String projectParentPath,String projectName,String d4jPath){
        this.projectParentPath=projectParentPath;
        this.projectName=projectName;
        this.d4jPath=d4jPath;

        String[] temp=projectName.split("_");
        this.subject=temp[0];
        this.version=Integer.valueOf(temp[1]);
    }

    /**
     * Checkout fixed version with defects4j.
     * @throws IOException Thrown by {@link ShellUtils#shellRun(List, String)}
     */
    private void checkoutFixedVersion() throws IOException{
        log.info("Checkout fixed version in "+projectParentPath+projectName+"f");
        List<String> cmd=new ArrayList<>();
        cmd.add(d4jPath + "framework/bin/defects4j checkout -p "+subject+" -v "+Integer.toString(version)+"f -w "+projectParentPath+projectName+"f");
        
        ShellUtils.shellRun(cmd,projectName);
    }

    private void removeFixedVersion() throws IOException{
        log.info("Remove fixed version in "+projectParentPath+projectName+"f");
        List<String> cmd=new ArrayList<>();
        cmd.add("rm -rf "+projectParentPath+projectName+"f");
        
        ShellUtils.shellRun(cmd,projectName);
    }

    /**
     * Checkout clean buggy version.
     * @throws IOException Thrown by {@link ShellUtils#shellRun(List, String)}
     */
    public void checkoutBuggyVersion() throws IOException{
        log.info("Checkout buggy version in "+projectParentPath+projectName);
        List<String> cmd=new ArrayList<>();
        cmd.add("rm -rf "+projectParentPath+projectName);
        ShellUtils.shellRun(cmd, projectName);

        cmd.clear();
        cmd.add(d4jPath + "framework/bin/defects4j checkout -p "+subject+" -v "+Integer.toString(version)+"b -w "+projectParentPath+projectName);
        ShellUtils.shellRun(cmd,projectName);

        cmd.clear();
        cmd.add(d4jPath + "framework/bin/defects4j compile -w "+projectParentPath+projectName);
        ShellUtils.shellRun(cmd,projectName);

        cmd.clear();
        cmd.add(d4jPath + "framework/bin/defects4j test -w "+projectParentPath+projectName);
        ShellUtils.shellRun(cmd,projectName);
    }

    /**
     * Run all tests with fixed version, return all failed tests.
     * @return all failed tests in fixed version
     * @throws IOException Thrown by {@link ShellUtils#shellRun(List, String)}
     */
    public List<String> getFailedPassTests() throws IOException{
        log.info("Validate failed tests in fixed version");
        checkoutFixedVersion();

        List<String> result=new ArrayList<>();

        TestUtils.compileProjectWithDefects4j(projectParentPath+projectName+"f",d4jPath);
        int count=TestUtils.getFailTestNumInProject(projectParentPath+projectName+"f", d4jPath, result);
        log.info("Failed pass tests: "+Integer.toString(count));

        List<String> finalResult=new ArrayList<>();
        for (String test: result){
            test = test.substring(test.indexOf("-") + 1).trim();
            finalResult.add(test);
        }

        removeFixedVersion();
        return finalResult;
    }
}
