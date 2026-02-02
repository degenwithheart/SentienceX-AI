import "../styles/globals.css";
import { Toaster } from "sonner";
import { ThemeProvider, useTheme } from "../lib/theme";

function AppShell({ Component, pageProps }) {
  const { theme } = useTheme();
  return (
    <>
      <Toaster
        theme={theme}
        position="top-right"
        richColors={true}
        closeButton={true}
        toastOptions={{
          className: "toast",
          classNames: {
            title: "toastTitle",
            description: "toastDesc",
            actionButton: "toastAction",
            cancelButton: "toastCancel"
          }
        }}
      />
      <Component {...pageProps} />
    </>
  );
}

export default function App({ Component, pageProps }) {
  return (
    <ThemeProvider>
      <AppShell Component={Component} pageProps={pageProps} />
    </ThemeProvider>
  );
}
