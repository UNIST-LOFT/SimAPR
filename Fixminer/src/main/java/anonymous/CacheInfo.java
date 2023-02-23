package anonymous;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.List;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

import edu.lu.uni.serval.utils.FileUtils;

public class CacheInfo {
    public static class Cache{
        public String id;
        public boolean isCompilable;
        public long testTime;

        public Cache(String id, boolean isCompilable, long testTime) {
            this.id = id;
            this.isCompilable = isCompilable;
            this.testTime = testTime;
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;

            Cache cache = (Cache) o;

            return id.equals(cache.id);
        }

        @Override
        public String toString() {
            return id+" - compilable: "+Boolean.toString(isCompilable)+" - test time: "+Long.toString(testTime);
        }
    }

    private List<Cache> caches;
    public CacheInfo() {
        this.caches = new ArrayList<>();
    }

    public void appendCache(Cache cache) {
        System.out.println("Cached: "+cache.toString());
        this.caches.add(cache);
    }

    public boolean isCached(Cache cache){
        return this.caches.contains(cache);
    }

    public void saveCache(String file){
        JsonObject root=new JsonObject();
        for(Cache cache:caches){
            JsonObject cacheJson=new JsonObject();
            cacheJson.addProperty("basic", false);
            cacheJson.addProperty("plausible", false);
            cacheJson.addProperty("pass_all_fail", false);
            cacheJson.addProperty("compilable", cache.isCompilable);
            cacheJson.addProperty("fail_time", cache.testTime);
            cacheJson.addProperty("pass_time", 0.0);
            root.add(cache.id,cacheJson);
        }

        String cacheStr=root.toString();
        File f=new File(file);
        try{
            FileWriter writer=new FileWriter(f);
            writer.write(cacheStr);
            writer.close();
        }
        catch (Exception e){
            e.printStackTrace();
        }
    }
}
