package kr.ac.unist.apr;

import java.io.File;
import java.io.IOException;
import java.net.URISyntaxException;
import java.util.List;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

import kr.ac.unist.apr.SwitchInfo.FileInfo;
import kr.ac.unist.apr.SwitchInfo.FuncInfo;
import kr.ac.unist.apr.SwitchInfo.LineInfo;

import org.apache.commons.io.FileUtils;

import edu.lu.uni.serval.utils.FileHelper;

/**
 * Casino information generator.
 */
public class JsonInfo {
    /**
     * Inner class for fault location.
     */
    public static class Location {
        public String file;
        public int line;
        public double score;

        public Location(String file,int line,double score){
            this.file=file;
            this.line=line;
            this.score=score;
        }
    }

    private JsonObject root;
    private Gson gson;

    /**
     * Constructor with project name.
     * @param projectName project name (e.g. Math_50)
     */
    public JsonInfo(String projectName){
        gson=new GsonBuilder().setPrettyPrinting().create();
        root=new JsonObject();
        root.addProperty("project_name", projectName);
        root.add("priority", new JsonArray());
        root.add("rules", new JsonArray());
        root.add("ranking", new JsonArray());
    }

    /**
     * Save current informations.
     * @param fullProjectPath full path of current project (e.g. /.../Math_50)
     */
    public void saveToFile(String buggyProject){
        FileHelper.createFile(new File("d4j/"+buggyProject+"/switch-info.json"), gson.toJson(root));
    }

    /**
     * Set fail and pass test lists.
     * @param failTests list of failing tests
     * @param allTests list of all tests (failing tests+passing tests)
     */
    public void setTestList(List<String> failTests,List<String> allTests){
        // Add fail tests at info json
		root.add("failing_test_cases", new JsonArray());
		for (String test:failTests){
			root.get("failing_test_cases").getAsJsonArray().add(test);
		}

        // Add pass tests
        root.add("passing_test_cases", new JsonArray());
        for (String test:allTests){
            if (!failTests.contains(test)){
                root.get("passing_test_cases").getAsJsonArray().add(test);
            }
        }
    }

    /**
     * Set failed passing test(failed in fixed version) lists.
     * @param failTests list of failed passing tests
     */
    public void setFailedPassTest(List<String> failedPassTestList){
        JsonArray testArray=new JsonArray();
        for (String test:failedPassTestList){
            testArray.add(test);
        }
        root.add("failed_passing_tests", testArray);
    }

    /**
     * Add a faulty location.
     * @param location information of faulty location
     */
    public void addFaultLocation(Location location){
        JsonObject newObject=new JsonObject();
        newObject.addProperty("file", location.file);
        newObject.addProperty("line", location.line);
        newObject.addProperty("score", location.score);

        root.get("priority").getAsJsonArray().add(newObject);
    }

    /**
     * Add multiple faulty locations.
     * @param locations list of faulty locations
     */
    public void addFaultLocations(List<Location> locations){
        for (Location loc:locations)
            addFaultLocation(loc);
    }

    /**
     * Set patch space tree.
     * <p>
     * This method will remove previous patch space tree, and set to new one.
     * </p>
     * @param infos list of all patches files
     */
    public void setSwitchInfos(List<FileInfo> infos){
        JsonArray fileArray=new JsonArray();
        for (FileInfo info:infos){
            JsonObject fileObject=new JsonObject();
            fileObject.addProperty("file_name", info.fileName);
            fileObject.addProperty("class_name", info.className);

            JsonArray funcArray=new JsonArray();
            for (FuncInfo funcInfo:info.funcInfos){
                JsonObject funcObject=new JsonObject();
                funcObject.addProperty("function", funcInfo.funcName);

                JsonArray lineArray=new JsonArray();
                for (LineInfo lineInfo:funcInfo.lineInfos){
                    JsonObject lineObject=new JsonObject();
                    lineObject.addProperty("line", lineInfo.line);
                    lineObject.addProperty("fl_score", lineInfo.switchInfos.get(0).score);
                    lineObject.addProperty("id", lineInfo.id);

                    JsonArray switchArray=new JsonArray();
                    for (SwitchInfo switchInfo:lineInfo.switchInfos){
                        JsonObject switchObject=new JsonObject();
                        switchObject.addProperty("mutation", switchInfo.mutator.getSimpleName());
                        switchObject.addProperty("location", switchInfo.fixedSourcePath);
                        switchObject.addProperty("patch_id", switchInfo.id);

                        switchArray.add(switchObject);
                    }
                    lineObject.add("cases", switchArray);
                    lineArray.add(lineObject);
                }
                funcObject.add("lines", lineArray);
                funcArray.add(funcObject);
            }
            fileObject.add("functions", funcArray);
            fileArray.add(fileObject);
        }

        root.remove("rules");
        root.add("rules",fileArray);
    }

    /**
     * Copy original source to temp directory.
     * @param originalPath original source directory
     * @param dir temp directory
     * @throws IOException thrown by {@link FileUtils#copyDirectory(File, File)}
     * @throws URISyntaxException thrown by {@link FileUtils#copyDirectory(File, File)}
     */
    public static void copyOriginal(String originalPath,String dir) throws IOException, URISyntaxException{
        File origFile=new File(originalPath);
        File newFile=new File(dir);
        FileUtils.copyDirectory(origFile,newFile);
    }

    /**
     * Add a patch to static ranking.
     * @param patchedFilePath path of patched source file
     */
    public void addPatchRanking(String patchedFilePath){
        root.get("ranking").getAsJsonArray().add(patchedFilePath);
    }
}
