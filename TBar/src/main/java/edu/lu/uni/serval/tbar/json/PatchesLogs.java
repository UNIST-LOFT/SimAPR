package edu.lu.uni.serval.tbar.json;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import edu.lu.uni.serval.entity.Pair;
import edu.lu.uni.serval.tbar.TBarTransformerFixer;
import org.apache.commons.lang3.tuple.ImmutableTriple;
import org.apache.commons.lang3.tuple.Triple;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class PatchesLogs {

    private final static Logger log = LoggerFactory.getLogger(TBarTransformerFixer.class);

    private ObjectNode jsonBuilder;
    private final ObjectMapper mapper = new ObjectMapper();
    private final Map<String, Map<LineLevelInfo, ArrayList<MutationInfo>>> changeLogs;
    private final ArrayList<Pair<String, Integer>> priorities;
    private final ArrayList<Triple<String, Integer, Float>> extendedPriorities;
    private final Map<String, ArrayList<MethodMutationInfo>> mutatedMethods;
    private final ArrayList<String> failingTestCases;
    private final ArrayList<String> passingTestCases;
    private final ArrayList<String> failedPassingTest;
    private final ArrayList<MutationRanking> rankings;
    private final Map<String, String> javaToClassfile;
    private String projectName;

    public PatchesLogs() {
        this.jsonBuilder = mapper.createObjectNode();
        this.changeLogs = new HashMap<>();
        this.priorities = new ArrayList<>();
        this.mutatedMethods = new HashMap<>();
        this.failingTestCases = new ArrayList<>();
        this.passingTestCases = new ArrayList<>();
        this.failedPassingTest = new ArrayList<>();
        this.extendedPriorities = new ArrayList<>();
        this.rankings = new ArrayList<>();
        this.javaToClassfile = new HashMap<>();
    }

    public void setProjectName(String name) {
        this.projectName = name;
    }

    public void addLine(String file, int line, String mutationName, String location, int start, int end, float score) {
        initFieldsIfNecessary(file, line, score);
        MutationInfo info = new MutationInfo(mutationName, location, start, end, score);
        LineLevelInfo lineLevel = new LineLevelInfo(line, score);
        if (!changeLogs.get(file).get(lineLevel).add(info)) {
            log.error("Couldn't add " + mutationName + " to the " + file + ":" + line + "[" + start + ":" + end + "]");
        }
    }

    public void addPriority(String filename, int buggyLine) {
        this.priorities.add(new Pair<>(filename, buggyLine));
    }

    public void addPriority(String filename, int buggyLine, float score) {
        this.extendedPriorities.add(
                new ImmutableTriple<>(filename, buggyLine, score)
        );
    }

    public void addRanking(String location, int ranking) {
        this.rankings.add(new MutationRanking(location, ranking));
    }

    public void addMethodMutation(
            String filename,
            String methodName,
            String methodDesc,
            int startLine,
            int endLine
    ) {
        initMethodsIfNecessary(filename);
        MethodMutationInfo info = new MethodMutationInfo(methodName, methodDesc, startLine, endLine);
        if (mutatedMethods.get(filename).contains(info)) return;
        if (!mutatedMethods.get(filename).add(info)) {
            log.error("Couldn't add " + methodName + " to the " + filename + ":" + "[" + startLine + ":" + endLine + "]");
        }
    }

    public void addJavaToClassfile(String javaFile, String classFile) {
        if (!this.javaToClassfile.containsKey(javaFile)) {
            this.javaToClassfile.put(javaFile, classFile);
        }
    }

    private void initFieldsIfNecessary(String file, int line, float score) {
        if (!changeLogs.containsKey(file)) {
            changeLogs.put(file, new HashMap<LineLevelInfo, ArrayList<MutationInfo>>());
        }
        LineLevelInfo lineLevel = new LineLevelInfo(line, score);
        if (!changeLogs.get(file).containsKey(lineLevel)) {
            changeLogs.get(file).put(lineLevel, new ArrayList<MutationInfo>());
        }
    }

    private void initMethodsIfNecessary(String filename) {
        if (!mutatedMethods.containsKey(filename)) {
            mutatedMethods.put(filename, new ArrayList<MethodMutationInfo>());
        }
    }

    public void addFailingTestCase(String testcase) {
        this.failingTestCases.add(testcase);
    }

    public void addFailingTestCases(List<String> testcases) {
        this.failingTestCases.addAll(testcases);
    }

    public void addPassingTestCases(List<String> tests) {
        this.passingTestCases.addAll(tests);
    }

    public void addFailedPassingTests(List<String> tests) {
        this.failedPassingTest.addAll(tests);
    }

    public String createJsonObject() {
        // Project name
        jsonBuilder.put("project_name", this.projectName);

        // Failing Test cases
        ArrayNode failingCases = mapper.createArrayNode();
        for (String fail: this.failingTestCases) {
            failingCases.add(fail);
        }
        jsonBuilder.set("failing_test_cases", failingCases);

        ArrayNode passingCases = mapper.createArrayNode();
        for (String pass: this.passingTestCases) {
            passingCases.add(pass);
        }
        jsonBuilder.set("passing_test_cases", passingCases);

        ArrayNode failedPassingCases = mapper.createArrayNode();
        for (String neutral: this.failedPassingTest) {
            failedPassingCases.add(neutral);
        }
        jsonBuilder.set("failed_passing_tests", failedPassingCases);

        // Priority
        ArrayNode extendedPriority = mapper.createArrayNode();
        for (Triple<String, Integer, Float> triplet: this.extendedPriorities) {
            ObjectNode exPri = mapper.createObjectNode();
            exPri.put("file", triplet.getLeft());
            exPri.put("line", triplet.getMiddle());
            exPri.put("fl_score", triplet.getRight());
            extendedPriority.add(exPri);
        }
        jsonBuilder.set("priority", extendedPriority);

        // Rules
        ArrayNode rules = mapper.createArrayNode();
        for (String fileName: changeLogs.keySet()) {
            ObjectNode rule = mapper.createObjectNode();
            rule.put("file_name", fileName);
            if (this.javaToClassfile.containsKey(fileName)) {
                rule.put("class_name", this.javaToClassfile.get(fileName));
            } else {
                rule.put("class_name", "");
            }

            ArrayNode lines = mapper.createArrayNode();
            for (LineLevelInfo lineLevel: changeLogs.get(fileName).keySet()) {
                ArrayNode mutations = mapper.createArrayNode();
                for (MutationInfo info: changeLogs.get(fileName).get(lineLevel)) {
                    ObjectNode mutation = mapper.createObjectNode()
                            .put("mutation", info.mutationName)
                            .put("start_position", info.start)
                            .put("end_position", info.end)
                            .put("location", info.location);
//                            .put("score", info.score);
                    mutations.add(mutation);
                }
                ObjectNode line = mapper.createObjectNode()
                        .put("line", lineLevel.line)
                        .put("fl_score", lineLevel.score);
                line.set("switches", mutations);
                lines.add(line);
            }
            rule.set("lines", lines);
            rules.add(rule);
        }
        jsonBuilder.set("rules", rules);

        // Functions
        ArrayNode functions = mapper.createArrayNode();
        for (String filename: mutatedMethods.keySet()) {
            ObjectNode function = mapper.createObjectNode();
            ArrayNode methods = mapper.createArrayNode();
            for (MethodMutationInfo info: mutatedMethods.get(filename)) {
                ObjectNode method = mapper.createObjectNode();
                method.put("function", info.methodName)
                        .put("begin", info.start)
                        .put("end", info.end)
                        .put("descriptor", info.methodDesc);
                methods.add(method);
            }
            function.put("file", filename)
                    .set("functions", methods);
            functions.add(function);
        }
        jsonBuilder.set("func_locations", functions);

        // Rankings
        ArrayNode ranking = mapper.createArrayNode();
        for (MutationRanking rank: this.rankings) {
            ObjectNode r = mapper.createObjectNode()
                    .put("location", rank.location)
                    .put("rank", rank.ranking);
            ranking.add(r);
        }
        jsonBuilder.set("ranking", ranking);

        String json = null;
        try {
            json = mapper.writerWithDefaultPrettyPrinter().writeValueAsString(jsonBuilder);
        } catch (JsonProcessingException e) {
            e.printStackTrace();
        }

        return json;
    }

    public void flush() {
        this.jsonBuilder = mapper.createObjectNode();
        this.changeLogs.clear();
    }

    private static class LineLevelInfo {
        public final int line;
        public final float score;

        public LineLevelInfo(int line, float score) {
            this.line = line;
            this.score = score;
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            LineLevelInfo that = (LineLevelInfo) o;
            return line == that.line && Float.compare(that.score, score) == 0;
        }

        @Override
        public int hashCode() {
            return Objects.hash(line, score);
        }
    }

    private static class MutationInfo {

        public final int start;
        public final int end;
        public final String mutationName;
        public final String location;
        public final float score;

        MutationInfo(String mutationName, String location, int start, int end, float score) {
            this.end = end;
            this.start = start;
            this.mutationName = mutationName;
            this.location = location;
            this.score = score;
        }
    }

    private static class MethodMutationInfo {

        public final int start;
        public final int end;
        public final String methodName;
        public final String methodDesc;

        MethodMutationInfo(String methodName, String methodDesc, int start, int end) {
            this.end = end;
            this.start = start;
            this.methodName = methodName;
            this.methodDesc = methodDesc;
        }

        @Override
        public boolean equals(Object o) {
            if (o == null || getClass() != o.getClass()) return false;
            MethodMutationInfo that = (MethodMutationInfo) o;
            return start == that.start && end == that.end
                    && methodName.equals(that.methodName)
                    && methodDesc.equals(that.methodDesc);
        }
    }

    private static class MutationRanking {
        public final String location;
        public final int ranking;

        public MutationRanking(String location, int ranking) {
            this.location = location;
            this.ranking = ranking;
        }
    }
}
