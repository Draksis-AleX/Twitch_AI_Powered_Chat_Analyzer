package myapps;

import java.io.File;
import java.io.IOException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.StreamsBuilder;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Properties;
import java.util.Set;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.Files;
import java.nio.file.FileSystems;
import java.nio.file.WatchService;
import java.nio.file.StandardWatchEventKinds;
import java.nio.file.WatchKey;
import java.nio.file.WatchEvent;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.kstream.Consumed;
import org.slf4j.LoggerFactory;
import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;

public class EmojiFilterStream {

    private static KafkaStreams streams; // Variabile statica a livello di classe

    static {
        Logger logger = (Logger) LoggerFactory.getLogger("org.apache.kafka");
        logger.setLevel(Level.WARN);
        logger = (Logger) LoggerFactory.getLogger("kafka");
        logger.setLevel(Level.WARN);
    }

    public static void main(String[] args) {
        try {
            // Configurazione iniziale e avvio del servizio Kafka
            startKafkaService();

            // Avvio del monitoraggio del file emotes.json in un nuovo thread
            Path path = Paths.get("emotes.json");
            System.out.println("[DEBUG] - Path: " + path);
            Thread watcherThread = new Thread(() -> {
                try {
                    watchFileChanges(path);
                } catch (IOException | InterruptedException e) {
                    e.printStackTrace();
                }
            });
            watcherThread.start();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void startKafkaService() throws Exception {
        StreamsBuilder builder = new StreamsBuilder();
        ObjectMapper objectMapper = new ObjectMapper();
        ObjectMapper mapper = new ObjectMapper();

        Properties properties = new Properties();
        properties.put("bootstrap.servers", "host.docker.internal:9092");
        properties.put("application.id", "emoji-filter-app");

        try {

            // Carica le emote dal file emotes.json
            final Set<String>[] emojis = new Set[1];
            emojis[0] = mapper.readValue(new File("emotes.json"), Set.class);

            System.out.println(emojis[0]);

            // Filtra i messaggi che contengono emote
            builder.<String, String>stream("general", Consumed.with(Serdes.String(), Serdes.String()))
                    .filter((key, value) -> {
                        String content = "";
                        try {
                            JsonNode jsonNode = objectMapper.readTree(value);
                            content = jsonNode.get("content").asText();
                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                        System.out.println('\n' + content + '\n');
                        return Arrays.stream(content.split("\\s+"))
                                .noneMatch(word -> emojis[0].contains(word));
                    })
                    .to("no_emotes_general");

        } catch (IOException e) {
            e.printStackTrace();
        }

        try {
            streams = new KafkaStreams(builder.build(), properties);
            streams.start();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void watchFileChanges(Path path) throws IOException, InterruptedException {
        Path dirPath = path.toAbsolutePath().getParent();
        if (dirPath == null) {
            System.err.println("Il percorso assoluto non ha un genitore.");
            return;
        }

        WatchService watchService = FileSystems.getDefault().newWatchService();
        dirPath.register(watchService, StandardWatchEventKinds.ENTRY_MODIFY);

        long lastModifiedTime = 0;
        final long debounceTime = 3000; // Tempo di debounce in millisecondi

        while (true) {
            WatchKey key = watchService.take();
            for (WatchEvent<?> event : key.pollEvents()) {
                WatchEvent.Kind<?> kind = event.kind();
                if (kind.equals(StandardWatchEventKinds.ENTRY_MODIFY)) {
                    Path changed = (Path) event.context();
                    if (changed.endsWith(path.getFileName())) {
                        long currentTime = System.currentTimeMillis();
                        if (currentTime - lastModifiedTime > debounceTime) {
                            System.out.println("File emotes.json modificato. Riavvio del servizio...");
                            try {
                                restartKafkaService();
                            } catch (Exception e) {
                                System.err.println("Errore nel riavvio del servizio Kafka: " + e.getMessage());
                                e.printStackTrace();
                            }
                            lastModifiedTime = currentTime;
                        }
                    }
                }
            }
            if (!key.reset()) {
                break;
            }
        }
    }

    private static void restartKafkaService() throws Exception {
        if (streams != null) {
            streams.close();
        }
        startKafkaService();
    }
}