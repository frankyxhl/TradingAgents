import functools
import json
import time

from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
)


def create_trader(llm, memory):
    def trader_node(state, name):
        company_name = state["company_of_interest"]
        instrument_context = build_instrument_context(
            company_name, state.get("resolved_company_name")
        )
        investment_plan = state["investment_plan"]
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        if past_memories:
            for i, rec in enumerate(past_memories, 1):
                past_memory_str += rec["recommendation"] + "\n\n"
        else:
            past_memory_str = "No past memories found."

        lang_inst = get_language_instruction()
        if lang_inst:
            conclusion_fmt = "最终交易建议：**买入/持有/卖出**"
            user_content = f"基于分析师团队的综合分析，以下是为 {company_name} 制定的投资计划。{instrument_context} 该计划整合了当前技术面趋势、宏观经济指标和社交媒体情绪分析。请以此为基础做出交易决策。\n\n投资计划：{investment_plan}\n\n请利用以上信息做出明智的战略决策。"
            system_content = f"""你是一名交易员，负责分析市场数据并做出投资决策。基于你的分析，提供具体的买入、卖出或持有建议。以坚定的决策结尾，并始终以「{conclusion_fmt}」确认你的建议。运用过去决策中的经验教训加强分析。以下是你在类似情况下的交易反思和经验教训：{past_memory_str}{lang_inst}"""
        else:
            conclusion_fmt = "FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**"
            user_content = f"Based on a comprehensive analysis by a team of analysts, here is an investment plan tailored for {company_name}. {instrument_context} This plan incorporates insights from current technical market trends, macroeconomic indicators, and social media sentiment. Use this plan as a foundation for evaluating your next trading decision.\n\nProposed Investment Plan: {investment_plan}\n\nLeverage these insights to make an informed and strategic decision."
            system_content = f"""You are a trading agent analyzing market data to make investment decisions. Based on your analysis, provide a specific recommendation to buy, sell, or hold. End with a firm decision and always conclude your response with '{conclusion_fmt}' to confirm your recommendation. Apply lessons from past decisions to strengthen your analysis. Here are reflections from similar situations you traded in and the lessons learned: {past_memory_str}"""

        context = {"role": "user", "content": user_content}
        messages = [{"role": "system", "content": system_content}, context]

        result = llm.invoke(messages)

        return {
            "messages": [result],
            "trader_investment_plan": result.content,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")
