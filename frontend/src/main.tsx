import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/700.css';
import '@fontsource/jetbrains-mono/400.css';
import '@fontsource/jetbrains-mono/500.css';
import { queryClient } from './api/client';
import { App } from './app/App';
import './app/styles.css';

class ErrorBoundary extends React.Component<{children:React.ReactNode},{error:string|null}> {
  state={error:null as string|null};
  static getDerivedStateFromError(error:Error){return {error:error.message};}
  render(){return this.state.error?<div className="fatal-error"><h1>Console needs a refresh</h1><p>{this.state.error}</p><button className="button button-primary" onClick={()=>location.reload()}>Reload console</button></div>:this.props.children;}
}
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><ErrorBoundary><QueryClientProvider client={queryClient}><App/></QueryClientProvider></ErrorBoundary></React.StrictMode>);
