import Markdown from "react-markdown";
export function SafeMarkdown({ children }: { children: string }) {
  return (
    <div className="markdown">
      <Markdown
        skipHtml
        disallowedElements={[
          "img",
          "iframe",
          "script",
          "style",
          "input",
          "button",
        ]}
        unwrapDisallowed
        components={{
          a: ({ node, ...props }) => (
            <a {...props} target="_blank" rel="noreferrer" />
          ),
        }}
      >
        {children}
      </Markdown>
    </div>
  );
}
