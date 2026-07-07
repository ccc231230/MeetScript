import { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Upload, Form, Input, Select, Button, Typography, Progress, App, Steps, Tag, Tooltip } from 'antd';
import { InboxOutlined, VideoCameraOutlined, CloudUploadOutlined, CheckCircleOutlined, PlayCircleOutlined, GlobalOutlined, RobotOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { meetingsAPI } from '../../api/meetings';
import { modelsAPI } from '../../api/models';
import type { UploadFile } from 'antd/es/upload/interface';
import type { ModelConfig } from '../../types';

const { Title, Text } = Typography;
const { Dragger } = Upload;

const LANGUAGES = [
  { value: 'zh', label: '🇨🇳 中文' },
  { value: 'en', label: '🇺🇸 English' },
  { value: 'ja', label: '🇯🇵 日本語' },
  { value: 'ko', label: '🇰🇷 한국어' },
  { value: 'fr', label: '🇫🇷 Français' },
  { value: 'de', label: '🇩🇪 Deutsch' },
  { value: 'es', label: '🇪🇸 Español' },
];

function getUploadErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status;
    const detail = err.response?.data?.detail;
    if (detail && typeof detail === 'string') return detail;
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

  // Fetch active model configs
  const { data: modelConfigs } = useQuery({
    queryKey: ['model-configs'],
    queryFn: async () => {
      const res = await modelsAPI.list();
      return (res.data || []).filter((c: ModelConfig) => c.is_active);
    },
    staleTime: 60_000,
  });

  const activeModel = (type: string) =>
    modelConfigs?.find((c: ModelConfig) => c.model_type === type);

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
      setCurrentStep(0);
      const uploadRes = await meetingsAPI.uploadFile(file, setUploadProgress);
      const objectKey = uploadRes.data.object_key;
      setUploadProgress(70);

      setCurrentStep(1);
      const fileType = file.type.startsWith('video/') ? 'video' : 'audio';
      await meetingsAPI.notifyUploadComplete({
        object_key: objectKey,
        file_name: file.name,
        file_size: file.size,
        file_type: fileType,
      });
      setUploadProgress(100);

      setCurrentStep(2);
      const meetingRes = await meetingsAPI.create({
        ...values,
        file_path: objectKey,
        file_type: fileType,
        file_size_bytes: file.size,
      });

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

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-3">
          <div
            className="flex items-center justify-center rounded-xl"
            style={{
              width: 44, height: 44,
              background: 'linear-gradient(135deg, #0D9488, #14B8A6)',
              boxShadow: '0 2px 8px rgba(13,148,136,0.3)',
            }}
          >
            <CloudUploadOutlined className="text-white text-xl" />
          </div>
          <div>
            <Title level={4} className="!mb-0 !text-slate-800">上传会议录制</Title>
            <Text type="secondary">上传音频或视频文件，自动进行语音识别与纪要生成</Text>
          </div>
        </div>
      </div>

      {/* Upload Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {/* Model Selection Bar */}
        {modelConfigs && modelConfigs.length > 0 && (
          <div className="px-8 py-4 bg-gradient-to-r from-slate-50 to-white border-b border-slate-100">
            <div className="flex items-center gap-2 mb-2">
              <Text className="text-xs font-medium text-slate-500 uppercase tracking-wider">当前模型配置</Text>
              <Tooltip title="在「模型配置」页面切换模型">
                <Tag color="blue" className="text-xs cursor-pointer" onClick={() => navigate('/models')}>
                  切换 →
                </Tag>
              </Tooltip>
            </div>
            <div className="flex flex-wrap gap-3">
              {(['asr', 'translation', 'summary'] as const).map((type) => {
                const cfg = activeModel(type);
                const icons: Record<string, React.ReactNode> = {
                  asr: <PlayCircleOutlined />,
                  translation: <GlobalOutlined />,
                  summary: <RobotOutlined />,
                };
                const labels: Record<string, string> = {
                  asr: '语音识别',
                  translation: '翻译',
                  summary: '总结',
                };
                return (
                  <div
                    key={type}
                    className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-sm"
                  >
                    <span className="text-teal-600 text-sm">{icons[type]}</span>
                    <Text className="text-xs text-slate-500">{labels[type]}</Text>
                    <Tag color={cfg ? 'green' : 'default'} className="text-xs m-0">
                      {cfg?.model_name ?? '未配置'}
                    </Tag>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Upload Area */}
        <div className="p-8">
          <Form form={form} layout="vertical" size="large">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              <Form.Item
                name="title"
                label={<span className="font-medium text-slate-700">会议标题</span>}
                rules={[{ required: true, message: '请输入会议标题' }]}
                className="md:col-span-2"
              >
                <Input
                  placeholder="例如：2024年Q4产品规划评审会"
                  className="rounded-lg"
                />
              </Form.Item>

              <Form.Item
                name="source_language"
                label={<span className="font-medium text-slate-700">源语言</span>}
                rules={[{ required: true, message: '请选择源语言' }]}
                initialValue="zh"
              >
                <Select options={LANGUAGES} className="rounded-lg" />
              </Form.Item>

              <Form.Item name="description" label={<span className="font-medium text-slate-700">会议描述（可选）</span>}>
                <Input placeholder="简要描述会议内容..." className="rounded-lg" />
              </Form.Item>
            </div>

            <Form.Item
              label={<span className="font-medium text-slate-700">会议录制文件</span>}
              required
            >
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
                className="rounded-xl"
                style={{ borderColor: '#CBD5E1' }}
              >
                <p className="ant-upload-drag-icon mb-3">
                  <InboxOutlined className="text-primary-500" style={{ fontSize: 48 }} />
                </p>
                <p className="text-base font-medium text-slate-700 mb-1">
                  点击或拖拽文件到此区域上传
                </p>
                <p className="text-sm text-slate-400">
                  支持 MP4、MOV、AVI、WAV、MP3、M4A、FLAC 格式，最大 2GB
                </p>
                {fileList.length > 0 && (
                  <div className="mt-3 inline-flex items-center gap-2 bg-primary-50 text-primary-700 px-3 py-1.5 rounded-lg text-sm">
                    <VideoCameraOutlined />
                    <span className="font-medium">{fileList[0].name}</span>
                    <span className="text-primary-400">
                      ({formatFileSize(fileList[0].size || 0)})
                    </span>
                  </div>
                )}
              </Dragger>
            </Form.Item>

            {/* Progress */}
            {uploading && (
              <div className="mb-6 p-5 bg-slate-50 rounded-xl border border-slate-100">
                <Steps
                  current={currentStep}
                  size="small"
                  items={[
                    { title: '上传文件', icon: <CloudUploadOutlined /> },
                    { title: '验证文件', icon: <CheckCircleOutlined /> },
                    { title: '开始处理', icon: <VideoCameraOutlined /> },
                  ]}
                />
                <Progress
                  percent={uploadProgress}
                  status="active"
                  strokeColor={{ from: '#0D9488', to: '#2DD4BF' }}
                  className="mt-4"
                />
              </div>
            )}

            <Button
              type="primary"
              onClick={handleUpload}
              loading={uploading}
              disabled={fileList.length === 0}
              size="large"
              block
              className="h-12 rounded-lg font-semibold text-base"
              style={{
                background: 'linear-gradient(135deg, #0D9488, #14B8A6)',
                border: 'none',
                boxShadow: '0 4px 14px rgba(13,148,136,0.35)',
              }}
            >
              {uploading ? '正在上传...' : '上传并开始处理'}
            </Button>
          </Form>
        </div>

        {/* Footer tips */}
        <div className="px-8 py-4 bg-slate-50 border-t border-slate-100">
          <div className="flex flex-wrap gap-4 text-xs text-slate-400">
            <span>🔒 上传文件全程加密传输</span>
            <span>⚡ 处理时间取决于文件大小</span>
            <span>📊 处理后可在会议详情页查看</span>
          </div>
        </div>
      </div>
    </div>
  );
}
