from mcp.server.fastmcp import FastMCP
from vuln_loader import list_vulns, get_vuln

mcp = FastMCP("webvuln-ai")

@mcp.tool()
def list_vulnerabilities():
    """Return all vulnerability titles"""
    return list_vulns()

@mcp.tool()
def read_vulnerability(vuln_id: int):
    """Return full markdown for vulnerability"""
    return get_vuln(vuln_id)

if __name__ == "__main__":
    mcp.run()