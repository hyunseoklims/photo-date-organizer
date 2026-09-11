# 웹 버전

Chrome 또는 Edge에서 `index.html`을 HTTPS 웹 서버 또는 `localhost`로 열어 사용합니다.

- 원본·결과 폴더는 사용자가 직접 선택하고 권한을 허용합니다.
- 사진은 서버로 업로드되지 않으며 브라우저가 로컬 폴더 안에서 복사합니다.
- 브라우저 보안 정책상 Firefox·Safari에서는 폴더 쓰기 기능을 지원하지 않을 수 있습니다.

간단한 로컬 실행 방법:

```powershell
cd web
py -m http.server 8000
```

그 다음 Chrome 또는 Edge에서 `http://localhost:8000`을 엽니다.

Windows에서는 `웹앱_실행.bat`을 더블클릭하면 `http://localhost:8765` 서버를 열 수 있습니다. 서버를 끄려면 배치 파일 창에서 `Ctrl+C`를 누릅니다.
