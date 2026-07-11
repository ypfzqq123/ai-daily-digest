<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <xsl:output method="html" encoding="UTF-8" indent="yes"
              doctype-system="about:legacy-compat"/>

  <xsl:template match="/rss/channel">
    <html lang="zh-Hans">
    <head>
      <meta charset="UTF-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
      <title><xsl:value-of select="title"/></title>
      <style>
        :root { color-scheme: dark; }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          background: #0d1117; color: #e6edf3; line-height: 1.7;
          padding: 0 0 80px;
        }
        a { color: #58a6ff; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .wrap { max-width: 760px; margin: 0 auto; padding: 0 24px; }
        .head {
          display: flex; gap: 24px; align-items: center; flex-wrap: wrap;
          padding: 48px 0 32px;
        }
        .head img {
          width: 160px; height: 160px; border-radius: 20px;
          box-shadow: 0 8px 30px rgba(0,0,0,.5); flex-shrink: 0;
        }
        .head .meta { flex: 1; min-width: 240px; }
        .head h1 {
          font-size: 30px; font-weight: 800; margin-bottom: 10px;
          background: linear-gradient(135deg, #58a6ff, #bc8cff);
          -webkit-background-clip: text; background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        .head p { color: #8b949e; font-size: 15px; }
        .subscribe {
          background: linear-gradient(135deg, rgba(31,111,235,.12), rgba(188,140,255,.08));
          border: 1px solid rgba(88,166,255,.25); border-radius: 14px;
          padding: 20px 24px; margin-bottom: 36px;
        }
        .subscribe h2 { font-size: 15px; color: #58a6ff; margin-bottom: 10px; }
        .subscribe p { font-size: 13px; color: #8b949e; margin-bottom: 12px; }
        .xyz-btn {
          display: inline-block;
          background: linear-gradient(135deg, #1f6feb, #bc8cff);
          color: #fff; font-weight: 600; font-size: 14px;
          padding: 11px 24px; border-radius: 999px;
        }
        .xyz-btn:hover { filter: brightness(1.08); text-decoration: none; }
        .feed-url {
          display: inline-block; background: #161b22; border: 1px solid #30363d;
          border-radius: 8px; padding: 8px 14px; font-size: 13px;
          color: #c9d1d9; word-break: break-all; font-family: ui-monospace, monospace;
        }
        .ep {
          background: #161b22; border: 1px solid #21262d; border-radius: 12px;
          padding: 18px 22px; margin-bottom: 14px;
        }
        .ep .ep-title { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
        .ep .ep-sub { font-size: 12px; color: #8b949e; margin-bottom: 12px; }
        .ep audio { width: 100%; height: 38px; }
        .ep details { margin-top: 12px; }
        .ep summary { font-size: 13px; color: #58a6ff; cursor: pointer; }
        .ep .notes { font-size: 13px; color: #8b949e; margin-top: 10px; white-space: pre-wrap; }
        .foot { text-align: center; color: #484f58; font-size: 13px; margin-top: 40px; }
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="head">
          <img src="{itunes:image/@href}" alt="cover"/>
          <div class="meta">
            <h1><xsl:value-of select="title"/></h1>
            <p><xsl:value-of select="description"/></p>
          </div>
        </div>

        <div class="subscribe">
          <h2>🎧 如何订阅</h2>
          <p>推荐在小宇宙收听（手机 App 体验最佳）。用 Apple 播客 / Pocket Casts 的朋友可以复制下面的 RSS 订阅源添加。也可以直接点下面每期的播放按钮试听。</p>
          <p style="margin-bottom:14px;">
            <a class="xyz-btn" href="https://www.xiaoyuzhoufm.com/podcast/6a325e149357568efe4741ef" target="_blank" rel="noopener">🎧 在小宇宙收听</a>
          </p>
          <span class="feed-url"><xsl:value-of select="link"/>podcast.xml</span>
        </div>

        <xsl:for-each select="item">
          <div class="ep">
            <div class="ep-title"><xsl:value-of select="title"/></div>
            <div class="ep-sub">
              <xsl:value-of select="pubDate"/>
              <xsl:if test="itunes:duration"> · <xsl:value-of select="itunes:duration"/></xsl:if>
            </div>
            <audio controls="controls" preload="none" src="{enclosure/@url}"></audio>
            <details>
              <summary>文稿 / Show notes</summary>
              <div class="notes"><xsl:value-of select="description"/></div>
            </details>
          </div>
        </xsl:for-each>

        <div class="foot">© AI Daily Digest · <a href="{link}">返回首页</a></div>
      </div>
    </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
