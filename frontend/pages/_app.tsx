import "@/styles/globals.css";
import type { AppProps } from "next/app";
import { ConfigProvider, Layout, Menu } from "antd";
import zhCN from "antd/locale/zh_CN";
import { useRouter } from "next/router";
import type { MenuProps } from "antd";

const { Header, Content } = Layout;

const menuItems: MenuProps["items"] = [
  { key: "/", label: "智能问答" },
  { key: "/manage", label: "年报管理" },
  { key: "/about", label: "关于" },
];

export default function App({ Component, pageProps }: AppProps) {
  const router = useRouter();

  return (
    <ConfigProvider locale={zhCN}>
      <Layout style={{ minHeight: "100vh" }}>
        <Header
          style={{
            display: "flex",
            alignItems: "center",
            background: "#001529",
          }}
        >
          <div
            style={{
              color: "#fff",
              fontSize: 18,
              fontWeight: "bold",
              marginRight: 40,
              whiteSpace: "nowrap",
            }}
          >
            财报智能问答
          </div>
          <Menu
            theme="dark"
            mode="horizontal"
            selectedKeys={[router.pathname]}
            items={menuItems}
            onClick={({ key }) => router.push(key)}
            style={{ flex: 1, minWidth: 0 }}
          />
        </Header>
        <Content style={{ padding: "24px 48px" }}>
          <Component {...pageProps} />
        </Content>
      </Layout>
    </ConfigProvider>
  );
}
