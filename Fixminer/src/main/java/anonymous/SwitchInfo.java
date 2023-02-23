package anonymous;

import java.util.ArrayList;
import java.util.List;

import edu.lu.uni.serval.templates.FixTemplate;

/**
 * Switch information, for patch space tree.
 */
public class SwitchInfo {
    /**
     * File information, for patch space tree.
     */
    static public class FileInfo{
        public String fileName;
        public String className;
        public List<LineInfo> lineInfos=new ArrayList<>();
        public FileInfo(String fileName,String className){
            this.fileName=fileName;
            this.className=className;
        }
    }
    /**
     * Line information, for patch space tree.
     * <p>
     * {@link FileInfo} contains this objects.
     * </p>
     */
    static public class LineInfo{
        public int line;
        public int id;
        public List<SwitchInfo> switchInfos=new ArrayList<>();
        public LineInfo(int line){
            this.line=line;
        }
    }

    /**
     * Mutation operator of this patch.
     */
    public Class<? extends FixTemplate> mutator;
    public int startOffset;
    public int endOffset;
    /**
     * Path of patched source file.
     */
    public String fixedSourcePath;
    /**
     * Static score of this patch.
     * <p>
     * Usually it is FL score.
     * </P>
     */
    public double score;
    /**
     * ID of this patch.
     */
    public int id;
}
