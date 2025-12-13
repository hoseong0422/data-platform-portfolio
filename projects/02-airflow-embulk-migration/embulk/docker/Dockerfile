#FROM openjdk:8-jre-slim
FROM eclipse-temurin:8-jre-jammy

# Embulk 0.11 환경 변수
ENV EMBULK_VERSION=0.11.5
ENV EMBULK_HOME=/root/.embulk

# 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    curl vim build-essential ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Embulk 디렉토리 생성
RUN mkdir -p $EMBULK_HOME/bin $EMBULK_HOME/lib/gems $EMBULK_HOME/lib/m2/repository

# Embulk 0.11.5 JAR 다운로드
RUN curl -L "https://github.com/embulk/embulk/releases/download/v${EMBULK_VERSION}/embulk-${EMBULK_VERSION}.jar" \
    -o $EMBULK_HOME/bin/embulk.jar

# JRuby 9.3.10.0 다운로드 (Ruby 2.6 호환, BigQuery 0.7+ 지원)
RUN curl -L "https://repo1.maven.org/maven2/org/jruby/jruby-complete/9.3.10.0/jruby-complete-9.3.10.0.jar" \
    -o $EMBULK_HOME/bin/jruby-complete.jar

# Embulk 실행 스크립트 생성
RUN echo '#!/bin/bash' > $EMBULK_HOME/bin/embulk \
    && echo 'exec java -Xmx2g -jar '"$EMBULK_HOME"'/bin/embulk.jar "$@"' >> $EMBULK_HOME/bin/embulk \
    && chmod +x $EMBULK_HOME/bin/embulk \
    && ln -sf $EMBULK_HOME/bin/embulk /usr/local/bin/embulk

# Embulk 0.11+ 설정 파일 생성
RUN echo "jruby=file://$EMBULK_HOME/bin/jruby-complete.jar" > $EMBULK_HOME/embulk.properties \
    && echo "gem_home=$EMBULK_HOME/lib/gems" >> $EMBULK_HOME/embulk.properties \
    && echo "gem_path=" >> $EMBULK_HOME/embulk.properties \
    && echo "m2_repo=$EMBULK_HOME/lib/m2/repository" >> $EMBULK_HOME/embulk.properties

# JDBC Driver 다운로드
RUN mkdir -p /opt/jdbc && \
    curl -fsSL https://repo1.maven.org/maven2/mysql/mysql-connector-java/5.1.49/mysql-connector-java-5.1.49.jar \
    -o /opt/jdbc/mysql-connector-java-5.1.49.jar    

# 환경 변수 설정
ENV PATH="$EMBULK_HOME/bin:/usr/local/bin:$PATH"

# msgpack 설치 (필수)
RUN embulk gem install msgpack -v 1.8.0 --platform java --no-document

# embulk gem을 정확한 버전으로 설치
RUN embulk gem install embulk -v $EMBULK_VERSION --no-document

# JRuby 및 gem 환경 초기화를 위한 더미 실행
RUN embulk --version || true

# MySQL 플러그인 설치
RUN embulk gem install embulk-input-mysql -v 0.13.2 --platform java --no-document

# BigQuery 0.7+ 필요 의존성을 최신 버전으로 설치
RUN embulk gem install jwt -v 3.1.2 --no-document
RUN embulk gem install public_suffix -v 5.1.1 --no-document
RUN embulk gem install multi_json -v 1.15.0 --no-document
RUN embulk gem install mini_mime -v 1.1.5 --no-document
RUN embulk gem install liquid -v 5.3.0 --no-document

# BigQuery 플러그인 0.7+ 설치 (Embulk 0.11 호환)
RUN embulk gem install embulk-output-bigquery -v 0.7.5 --no-document

# 설치된 gem 검증 (Embulk 0.11 + BigQuery 0.7)
RUN embulk gem list | grep -E "(embulk-input-mysql|embulk-output-bigquery)" \
    && echo "=== Plugin versions ===" \
    && embulk gem list | grep "embulk-output-bigquery" \
    && embulk gem list | grep "embulk-input-mysql"

RUN mkdir -p /app/config

COPY config.yml.liquid /app/config/job.yml.liquid
COPY test_config.yml.liquid /app/config/test_job.yml.liquid

WORKDIR /app

# 기본 명령어
# CMD ["/bin/bash"]
ENTRYPOINT ["embulk"]
CMD ["--version"]

