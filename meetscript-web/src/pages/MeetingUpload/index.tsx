import { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, Form, Input, Select, Button, Card, Typography, Progress, App, Steps } from 'antd';
import { InboxOutlined, VideoCameraOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { meetingsAPI } from '../../api/meetings';
import type { UploadFile } from 'antd/es/upload/interface';

const { Title } = Typography;
const { Dragger } = Upload;

const LANGUAGES = [
  { value: 'zh', label: '中文' },
  { value: 'en', label: 'English' },
  { value: 'ja', label: '日本語' },
  { value: 'ko', label: '한국어' },
  { value: 'fr', label: 'Français' },
  { value: 'de', label: 'Deutsch' },
  { value: 'es', label: 'Español' },
];

/** Extract a human-readable Chinese error message from an axios error. */
function getUploadErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status;
    const detail = err.response?.data?.detail;
    // Backend returns Chinese error messages in detail field
    if (detail && typeof detail === 'string') return detail;
    // Map common HTTP status codes to Chinese messages
    if (status === 413) return '文件过大，超过服务器限制';
    if (status === 422) return '请求格式错误，无法读取文件';
    if (status === 401) return '登录已过期，请重新登录';
    if (status === 429) return '请求过于频繁，请稍后重试';
    if (err.code === 'ECONNABORTED' || err.code === 'ERR_CANCELED') return '上传超时，请检查网络后重试';
    if (!err.response) return '网络连接失败，请检查网络后重试';
    return `上传失败 (${status})`;
  }
  if (err instanceof Error) return err.message;
  return '上传失败，请重试';
}

export default function MeetingUploadPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const pickedFileRef = useRef<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);

  const handleUpload = useCallback(async () => {
    const values = await form.validateFields();
    const file = pickedFileRef.current;
    if (!file) {
      message.warning('请选择要上传的文件');
      return;
    }

    setUploading(true);
    setCurrentStep(0);

    try {
      // Step 0: Upload file directly through backend
      setCurrentStep(0);
      const uploadRes = await meetingsAPI.uploadFile(file, setUploadProgress);
      const objectKey = uploadRes.data.object_key;

      setUploadProgress(70);

      // Step 1: Notify server upload complete
      setCurrentStep(1);
      const fileType = file.type.startsWith('video/') ? 'video' : 'audio';
      await meetingsAPI.notifyUploadComplete({
        object_key: objectKey,
        file_name: file.name,
        file_size: file.size,
        file_type: fileType,
      });

      setUploadProgress(100);

      // Step 2: Create meeting record & trigger processing
      setCurrentStep(2);
      const meetingRes = await meetingsAPI.create({
        ...values,
        file_path: objectKey,
        file_type: fileType,
        file_size_bytes: file.size,
      });

      // Step 3: Trigger processing
      await meetingsAPI.triggerProcess(meetingRes.data.id);

      message.success('上传成功，会议处理已开始');
      navigate(`/meetings/${meetingRes.data.id}`);
    } catch (err: unknown) {
      const errorMsg = getUploadErrorMessage(err);
      message.error(errorMsg);
    } finally {
      setUploading(false);
      setUploadProgress(0);
      setCurrentStep(0);
    }
  }, [fileList, form, message, navigate]);

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <Title level={4}>
        <VideoCameraOutlined style={{ marginRight: 8 }} />
        上传会议录制
      </Title>

      <Card>
        <Form form={form} layout="vertical">
          <Form.Item
            name="title"
            label="会议标题"
            rules={[{ required: true, message: '请输入会议标题' }]}
          >
            <Input placeholder="例如：2024年Q4产品规划评审会" />
          </Form.Item>

          <Form.Item name="description" label="会议描述">
            <Input.TextArea rows={3} placeholder="可选：简要描述会议内容" />
          </Form.Item>

          <Form.Item
            name="source_language"
            label="源语言"
            rules={[{ required: true, message: '请选择源语言' }]}
            initialValue="zh"
          >
            <Select options={LANGUAGES} />
          </Form.Item>

          <Form.Item label="会议录制文件" required>
            <Dragger
              maxCount={1}
              fileList={fileList}
              beforeUpload={(file) => {
                pickedFileRef.current = file;
                setFileList([file as unknown as UploadFile]);
                return false;
              }}
              onRemove={() => {
                pickedFileRef.current = null;
                setFileList([]);
              }}
              disabled={uploading}
            >
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
              <p className="ant-upload-hint">
                支持 MP4、MOV、AVI、WAV、MP3、M4A、FLAC 格式，最大 2GB
              </p>
            </Dragger>
          </Form.Item>

          {uploading && (
            <div style={{ marginBottom: 16 }}>
              <Steps
                current={currentStep}
                size="small"
                items={[
                  { title: '上传文件' },
                  { title: '验证文件' },
                  { title: '开始处理' },
                ]}
              />
              <Progress percent={uploadProgress} status="active" style={{ marginTop: 12 }} />
            </div>
          )}

          <Form.Item>
            <Button
              type="primary"
              onClick={handleUpload}
              loading={uploading}
              disabled={fileList.length === 0}
              size="large"
              block
            >
              {uploading ? '正在上传...' : '上传并开始处理'}
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
