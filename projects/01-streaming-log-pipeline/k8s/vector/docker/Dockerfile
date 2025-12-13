FROM timberio/vector:nightly-2025-09-24-debian

# 작업 디렉토리 생성
WORKDIR /etc/vector

EXPOSE 8686 9090

# Vector 실행
 CMD ["-c", "/etc/vector/vector.yaml"]