import os
import asyncio
import json
from openai import AsyncOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Define MCP servers
CCXT_PARAMS = StdioServerParameters(
    command="python3",
    args=["mcp_servers/mcp-server-ccxt/src/server.py"],
)

INDICATORS_PARAMS = StdioServerParameters(
    command="node",
    args=["mcp_servers/crypto-indicators-mcp/index.js"],
)

# LLM Configuration
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    raise ValueError("Please set DASHSCOPE_API_KEY environment variable.")

client = AsyncOpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

MODEL = "qwen3.6-plus"

SYSTEM_PROMPT = """
You are an autonomous AI trading agent capable of executing spot and futures trading strategies based on qualitative and quantitative analysis.
You have access to CCXT tools to fetch real-time and historical OHLCV data, and Technical Indicators tools to calculate RSI, MACD, etc.

Your objective:
1. Fetch recent OHLCV data for BTC/USDT (Spot) or futures if needed.
2. Calculate technical indicators (RSI, MACD) to understand the market regime.
3. Perform a multi-timeframe analysis.
4. Execute trades (or output a simulated decision) based on your dynamic hedging and trend following strategy.

When asked to evaluate the market, you MUST:
- Use get-historical-ohlcv to fetch data.
- Use indicators tools to calculate RSI/MACD.
- Output your reasoning and your final trading decision.
"""

def mcp_tool_to_openai_tool(mcp_tool):
    """Convert an MCP Tool schema to OpenAI Function Calling format."""
    return {
        "type": "function",
        "function": {
            "name": mcp_tool.name,
            "description": mcp_tool.description,
            "parameters": mcp_tool.inputSchema,
        }
    }

async def run_agent():
    # Connect to both MCP servers
    async with stdio_client(CCXT_PARAMS) as (ccxt_read, ccxt_write):
        async with ClientSession(ccxt_read, ccxt_write) as ccxt_session:
            await ccxt_session.initialize()
            
            async with stdio_client(INDICATORS_PARAMS) as (ind_read, ind_write):
                async with ClientSession(ind_read, ind_write) as ind_session:
                    await ind_session.initialize()

                    print("[+] Connected to CCXT and Crypto-Indicators MCP servers.")

                    # Fetch available tools
                    ccxt_tools = await ccxt_session.list_tools()
                    ind_tools = await ind_session.list_tools()

                    # Mapping tool names to their respective sessions
                    tool_map = {}
                    openai_tools = []

                    for t in ccxt_tools.tools:
                        openai_tools.append(mcp_tool_to_openai_tool(t))
                        tool_map[t.name] = ccxt_session
                    
                    for t in ind_tools.tools:
                        openai_tools.append(mcp_tool_to_openai_tool(t))
                        tool_map[t.name] = ind_session

                    # User Request
                    messages = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": "Analyze the BTC/USDT market on binance for the last 50 hours (1h timeframe). Give me your trading decision."}
                    ]

                    print("[+] Sending request to Qwen LLM...")
                    
                    while True:
                        response = await client.chat.completions.create(
                            model=MODEL,
                            messages=messages,
                            tools=openai_tools,
                        )

                        msg = response.choices[0].message
                        messages.append(msg)

                        if msg.tool_calls:
                            for tool_call in msg.tool_calls:
                                tool_name = tool_call.function.name
                                tool_args = json.loads(tool_call.function.arguments)
                                print(f"[LLM called tool: {tool_name}] with args: {tool_args}")

                                # Execute tool via MCP
                                target_session = tool_map.get(tool_name)
                                if target_session:
                                    try:
                                        result = await target_session.call_tool(tool_name, arguments=tool_args)
                                        # Parse result to text
                                        tool_result_text = "\n".join([c.text for c in result.content if c.type == "text"])
                                    except Exception as e:
                                        tool_result_text = f"Error executing tool: {e}"
                                else:
                                    tool_result_text = f"Error: Tool {tool_name} not found."
                                
                                print(f"[Tool Result]: {tool_result_text[:200]}...")
                                
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "name": tool_name,
                                    "content": tool_result_text
                                })
                        else:
                            print("\n[LLM Final Decision]")
                            print(msg.content)
                            break

if __name__ == "__main__":
    asyncio.run(run_agent())
