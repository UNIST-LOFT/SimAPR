package edu.lu.uni.serval.tbar.json.util;

import edu.lu.uni.serval.entity.Pair;
import org.apache.commons.io.FileUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;

public class PatchSpaceUtils {

    private final static Logger log = LoggerFactory.getLogger(PatchSpaceUtils.class);

    public final static int LINE_NOT_FOUND = -1;

    public static int getLineNumberOnPosition(String filename, long position) {
        try {
            BufferedReader br = new BufferedReader(new FileReader(filename));
            String line;
            long total_count = 0;
            int lineNumber = 0;
            while ((line = br.readLine()) != null) {
                line += "\n";
                total_count += line.length();
                lineNumber++;
                if (position <= total_count) {
                    return lineNumber;
                }
            }
            br.close();
        } catch (IOException io) {
            log.error("Cannot read line number for " + filename + " at " + position);
            log.error(io.getMessage());
        }
        return LINE_NOT_FOUND;
    }

    public static Pair<Integer, Integer> getLineNumberFromText(String filename, String text) {
        try {
            String code = getCodeFromFile(filename);
            long startIndex = code.indexOf(text);
            long endIndex = startIndex + text.length();
            log.error("Pair: " + startIndex + ":" + endIndex);
            return new Pair<>(
                    getLineNumberOnPosition(filename, startIndex),
                    getLineNumberOnPosition(filename, endIndex)
            );
        } catch (IOException io) {
            io.printStackTrace();
        }
        return null;
    }

    private static String getCodeFromFile(String filename) throws IOException {
        return FileUtils.readFileToString(new File(filename), "utf-8");
    }

}
