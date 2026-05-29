import { API } from "./client";

interface MessageResponse {
  message: string;
}

/**
 * パスワードリセットメールを送信します。
 * @param email 送信先メールアドレス
 */
export const requestPasswordReset = async (email: string): Promise<MessageResponse> => {
  const response = await API.post<MessageResponse>("/auth/reset-password", { email });
  return response.data;
};

/**
 * ログイン中ユーザーのパスワードを更新します。
 * @param newPassword 新しいパスワード（8文字以上）
 */
export const updatePassword = async (newPassword: string): Promise<MessageResponse> => {
  const response = await API.post<MessageResponse>("/auth/update-password", {
    new_password: newPassword,
  });
  return response.data;
};
