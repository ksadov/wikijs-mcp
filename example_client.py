# example_client.py
import argparse
import asyncio
import sys
from mcp import ClientSession, StdioServerParameters, Tool
from mcp.client.stdio import stdio_client


async def run_tests(
    query, action, page_id=None, page_path=None, content=None, description=None
):
    """Run tests against the Wiki.js MCP server"""
    # Create server parameters for stdio connection
    server_params = StdioServerParameters(command="python", args=["main.py"])

    # Connect to the MCP server
    async with stdio_client(server_params) as (read_stream, write_stream):
        # Create a client session
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the connection
            await session.initialize()

            # List available tools to confirm connection
            tools_response = await session.list_tools()
            tools = []

            for item in tools_response:
                if isinstance(item, tuple) and item[0] == "tools":
                    tools.extend(item[1])
            print(f"Available tools: {[tool.name for tool in tools]}\n")

            if action == "search":
                # Test search functionality
                print(f"Searching for: {query}")
                result = await session.call_tool(
                    "search_wiki", arguments={"query": query}
                )
                print("\nSearch Results:")
                print(result.content[0].text)

            elif action == "get":
                # Test page retrieval
                if page_id:
                    print(f"Getting page by ID: {page_id}")
                    result = await session.call_tool(
                        "get_page", arguments={"identifier": page_id, "by_path": False}
                    )
                elif page_path:
                    print(f"Getting page by path: {page_path}")
                    result = await session.call_tool(
                        "get_page", arguments={"identifier": page_path, "by_path": True}
                    )
                else:
                    print(
                        "Error: Either page_id or page_path must be provided for 'get' action"
                    )
                    return

                print("\nPage Content:")
                print(result.content[0].text)

            elif action == "update":
                if not page_id:
                    print("Error: page_id must be provided for 'update' action")
                    return
                if not content:
                    print("Error: content must be provided for 'update' action")
                    return

                # Test page update
                print(f"Updating page with ID: {page_id}")
                arguments = {"page_id": page_id, "content": content}
                if description:
                    arguments["description"] = description

                result = await session.call_tool("update_page", arguments=arguments)
                print("\nUpdate Result:")
                print(result.content[0].text)

            else:
                print(f"Unknown action: {action}")
                return


def main():
    parser = argparse.ArgumentParser(description="Test the Wiki.js MCP server")
    parser.add_argument(
        "action", choices=["search", "get", "update"], help="Action to perform"
    )
    parser.add_argument("--query", "-q", help="Search query")
    parser.add_argument("--page-id", "-i", help="Page ID for get/update operations")
    parser.add_argument("--page-path", "-p", help="Page path for get operation")
    parser.add_argument("--content", "-c", help="New content for update operation")
    parser.add_argument(
        "--description", "-d", help="New description for update operation"
    )

    args = parser.parse_args()

    # Validate arguments based on action
    if args.action == "search" and not args.query:
        parser.error("search action requires --query argument")

    if args.action == "get" and not (args.page_id or args.page_path):
        parser.error("get action requires either --page-id or --page-path argument")

    if args.action == "update" and (not args.page_id or not args.content):
        parser.error("update action requires --page-id and --content arguments")

    # Run the tests
    asyncio.run(
        run_tests(
            query=args.query,
            action=args.action,
            page_id=args.page_id,
            page_path=args.page_path,
            content=args.content,
            description=args.description,
        )
    )


if __name__ == "__main__":
    main()
