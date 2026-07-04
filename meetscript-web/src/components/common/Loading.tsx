import { Spin } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';

interface LoadingProps {
  tip?: string;
  fullScreen?: boolean;
}

export default function Loading({ tip = '加载中...', fullScreen = false }: LoadingProps) {
  if (fullScreen) {
    return (
      <div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'rgba(255,255,255,0.8)',
          zIndex: 9999,
        }}
      >
        <Spin indicator={<LoadingOutlined spin />} size="large" tip={tip}>
          <div style={{ padding: 50 }} />
        </Spin>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: '40px 0' }}>
      <Spin indicator={<LoadingOutlined spin />} tip={tip}>
        <div style={{ padding: 30 }} />
      </Spin>
    </div>
  );
}
