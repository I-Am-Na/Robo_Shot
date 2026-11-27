/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  /** 결제 QR 링크의 기준 주소. 휴대폰에서 열려면 PC IP 주소로 설정 (예: http://192.168.0.10:5173) */
  readonly VITE_PUBLIC_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
