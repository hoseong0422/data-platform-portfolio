# 기본 HTTP Sink Connector 설정
# text 필드의 메시지를 슬랙으로 발송

curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "http-sink-to-slack",
    "config": {
      "connector.class": "io.confluent.connect.http.HttpSinkConnector",
      "tasks.max": "1",
      "topics": "mock-alert",
      "http.api.url": "https://hooks.slack.com/services/XXX/XXX/XXX",
      "request.method": "POST",
      "headers": "Content-Type:application/json|Accept:application/json",
      "behavior.on.null.values": "ignore",
      "behavior.on.error": "log",
      "consumer.override.auto.offset.reset": "latest",
      "confluent.topic.bootstrap.servers": "broker-01:9092,broker-02:9092,broker-03:9092",
      "reporter.bootstrap.servers": "broker-01:9092,broker-02:9092,broker-03:9092",
      "reporter.error.topic.name": "connect-errors",
      "reporter.result.topic.name": "connect-success",
      "value.converter": "org.apache.kafka.connect.storage.StringConverter",
      "key.converter": "org.apache.kafka.connect.storage.StringConverter"
    }
  }'