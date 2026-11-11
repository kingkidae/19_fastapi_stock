# 19_fastapi_stock

삼성전자(005930) 주가 대시보드. FastAPI + FinanceDataReader.

- `/` 대시보드 페이지
- `/samsung` 주가·지표 JSON

## 로컬 실행

```
uv run uvicorn main:app --reload
```

## 배포 (AWS EC2, 시드니 리전)

`master`에 push하면 1분 안에 서버에 자동 반영됩니다.

- 서버가 1분마다 GitHub `master`를 확인해서 새 커밋이 있으면 `uv sync` 후 앱을 재시작합니다 ([deploy/update.sh](deploy/update.sh)).
- 설치에 실패하면 이전 버전이 계속 실행되고, 다음 1분에 다시 시도합니다.
- 서버를 새로 만들 때는 [deploy/setup.sh](deploy/setup.sh)를 user-data로 넘기면 설치부터 자동 배포 설정까지 끝납니다.

```
aws ec2 run-instances --region ap-southeast-2 --image-id <Ubuntu AMI> --instance-type t3.micro \
  --security-group-ids <80번 포트 열린 SG> --user-data file://deploy/setup.sh
```
