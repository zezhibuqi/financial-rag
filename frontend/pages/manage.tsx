import Head from "next/head";
import { useState, useEffect } from "react";
import { Upload, Table, message, Button } from "antd";
import { UploadOutlined, ReloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";

interface DocRecord {
  doc_name: string;
  company: string;
  year: number;
  chunk_count: number;
  uploaded_at: string;
}

export default function Manage() {
  const [data, setData] = useState<DocRecord[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchDocs = () => {
    setLoading(true);
    fetch("/api/docs")
      .then((r) => r.json())
      .then((d) => {
        if (d.error) {
          message.error(d.error);
        } else {
          setData(d.docs || []);
        }
      })
      .catch(() => message.error("加载失败"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  const columns: ColumnsType<DocRecord> = [
    { title: "年报名称", dataIndex: "doc_name", key: "doc_name" },
    { title: "公司", dataIndex: "company", key: "company", width: 100 },
    { title: "年份", dataIndex: "year", key: "year", width: 80 },
    {
      title: "Chunk 数量",
      dataIndex: "chunk_count",
      key: "chunk_count",
      width: 110,
    },
    {
      title: "入库时间",
      dataIndex: "uploaded_at",
      key: "uploaded_at",
      width: 180,
      render: (v: string) => new Date(v).toLocaleString("zh-CN"),
    },
  ];

  return (
    <>
      <Head>
        <title>年报管理 - 财报智能问答系统</title>
      </Head>

      <div style={{ marginBottom: 16, display: "flex", gap: 12 }}>
        <Upload
          action="/api/upload"
          accept=".pdf"
          showUploadList={false}
          onChange={(info) => {
            if (info.file.status === "done") {
              message.success(info.file.response?.msg || "上传成功");
            } else if (info.file.status === "error") {
              message.error("上传失败");
            }
          }}
        >
          <Button icon={<UploadOutlined />}>上传 PDF 年报</Button>
        </Upload>
        <Button icon={<ReloadOutlined />} onClick={fetchDocs} loading={loading}>
          刷新列表
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={data}
        rowKey="doc_name"
        loading={loading}
        pagination={false}
        locale={{ emptyText: "暂无已入库年报" }}
      />
    </>
  );
}
