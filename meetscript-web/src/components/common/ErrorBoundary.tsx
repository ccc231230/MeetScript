import { Component, ErrorInfo, ReactNode } from 'react';
import { Result, Button } from 'antd';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <Result
          status="error"
          title="页面出错了"
          subTitle={this.state.error?.message ?? '发生了未知错误'}
          extra={[
            <Button key="retry" type="primary" onClick={this.handleReset}>
              重试
            </Button>,
            <Button key="refresh" onClick={() => window.location.reload()}>
              刷新页面
            </Button>,
          ]}
        />
      );
    }

    return this.props.children;
  }
}
