#!/usr/bin/env python3
"""
Command Line Interface for Inventory Reservation Service.
Allows users to interact with the inventory system through the terminal.
"""
import asyncio
import httpx
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from typing import Optional
import json
from uuid import UUID

console = Console()

# Default API base URL
API_BASE_URL = "http://localhost:8000"


def print_success(message: str):
    """Print success message."""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str):
    """Print error message."""
    console.print(f"[red]✗[/red] {message}")


def print_info(message: str):
    """Print info message."""
    console.print(f"[blue]ℹ[/blue] {message}")


def get_error_detail(response: httpx.Response) -> str:
    """Safely extract error detail from HTTP response."""
    try:
        error_json = response.json()
        return error_json.get('detail', error_json.get('message', str(error_json)))
    except (json.JSONDecodeError, ValueError):
        # If response is not JSON, return the text
        return response.text or f"HTTP {response.status_code}"


@click.group(invoke_without_command=True)
@click.option('--url', default=API_BASE_URL, help='API base URL')
@click.pass_context
def cli(ctx, url):
    """Inventory Reservation Service CLI"""
    ctx.ensure_object(dict)
    ctx.obj['url'] = url
    
    # If no command provided, run interactive mode
    if ctx.invoked_subcommand is None:
        # Call interactive function directly, not as a Click command
        run_interactive(ctx.obj['url'])


def _list_products_impl(url: str):
    """List all products (SKUs) with inventory information - implementation."""
    api_url = f"{url}/api/v1/skus"
    
    try:
        with httpx.Client() as client:
            response = client.get(api_url)
            response.raise_for_status()
            products = response.json()
            
            if not products:
                console.print("[yellow]No products found in database.[/yellow]")
                return
            
            table = Table(title="Products Inventory", show_header=True, header_style="bold magenta")
            table.add_column("SKU Code", style="cyan", no_wrap=True)
            table.add_column("Name", style="green")
            table.add_column("Total", justify="right", style="blue")
            table.add_column("Reserved", justify="right", style="yellow")
            table.add_column("Allocated", justify="right", style="orange1")
            table.add_column("Available", justify="right", style="green")
            
            for product in products:
                table.add_row(
                    product['sku_code'],
                    product['name'],
                    str(product['total_qty']),
                    str(product['reserved_qty']),
                    str(product['allocated_qty']),
                    str(product['available_qty'])
                )
            
            console.print(table)
            console.print(f"\n[dim]Total products: {len(products)}[/dim]")
            
    except httpx.HTTPStatusError as e:
        print_error(f"API Error: {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        print_error(f"Connection Error: Could not connect to {api_url}")
        print_info("Make sure the server is running: uvicorn app.main:app --reload")
    except Exception as e:
        print_error(f"Error: {str(e)}")


@cli.command()
@click.pass_context
def list_products(ctx):
    """List all products (SKUs) with inventory information."""
    _list_products_impl(ctx.obj['url'])


def _create_product_impl(url: str):
    """Create a new product (SKU) - implementation."""
    console.print("\n[bold]Create New Product[/bold]\n")
    
    sku_code = Prompt.ask("SKU Code", default="")
    if not sku_code:
        print_error("SKU Code is required")
        return
    
    name = Prompt.ask("Product Name", default="")
    if not name:
        print_error("Product Name is required")
        return
    
    description = Prompt.ask("Description (optional)", default="")
    initial_qty = Prompt.ask("Initial Quantity", default="0")
    
    try:
        initial_qty = int(initial_qty)
    except ValueError:
        print_error("Initial quantity must be a number")
        return
    
    data = {
        "sku_code": sku_code,
        "name": name,
        "description": description if description else None,
        "initial_qty": initial_qty
    }
    
    api_url = f"{url}/api/v1/skus"
    
    try:
        with httpx.Client() as client:
            response = client.post(api_url, json=data)
            response.raise_for_status()
            product = response.json()
            
            print_success(f"Product created successfully!")
            console.print(f"\n[bold]Product Details:[/bold]")
            console.print(f"  SKU ID: {product['sku_id']}")
            console.print(f"  SKU Code: {product['sku_code']}")
            console.print(f"  Name: {product['name']}")
            
    except httpx.HTTPStatusError as e:
        error_detail = get_error_detail(e.response)
        print_error(f"Failed to create product: {error_detail}")
    except httpx.RequestError as e:
        print_error(f"Connection Error: Could not connect to {api_url}")
    except Exception as e:
        print_error(f"Error: {str(e)}")


@cli.command()
@click.pass_context
def create_product(ctx):
    """Create a new product (SKU)."""
    _create_product_impl(ctx.obj['url'])


def _availability_impl(url: str):
    """Check availability for all products or specific SKUs - implementation."""
    api_url = f"{url}/api/v1/inventory/availability"
    
    try:
        with httpx.Client() as client:
            response = client.get(api_url)
            response.raise_for_status()
            availability_data = response.json()
            
            if not availability_data:
                console.print("[yellow]No inventory data found.[/yellow]")
                return
            
            table = Table(title="Inventory Availability", show_header=True, header_style="bold magenta")
            table.add_column("SKU ID", style="cyan", no_wrap=True)
            table.add_column("Total", justify="right", style="blue")
            table.add_column("Reserved", justify="right", style="yellow")
            table.add_column("Allocated", justify="right", style="orange1")
            table.add_column("Available", justify="right", style="green")
            table.add_column("Version", justify="right", style="dim")
            
            for item in availability_data:
                table.add_row(
                    str(item['sku_id']),
                    str(item['total_qty']),
                    str(item['reserved_qty']),
                    str(item['allocated_qty']),
                    str(item['available_qty']),
                    str(item['version'])
                )
            
            console.print(table)
            
    except httpx.HTTPStatusError as e:
        print_error(f"API Error: {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        print_error(f"Connection Error: Could not connect to {api_url}")
    except Exception as e:
        print_error(f"Error: {str(e)}")


@cli.command()
@click.pass_context
def availability(ctx):
    """Check availability for all products or specific SKUs."""
    _availability_impl(ctx.obj['url'])


def _create_hold_impl(url: str):
    """Create a hold reservation - implementation."""
    console.print("\n[bold]Create Hold Reservation[/bold]\n")
    
    client_token = Prompt.ask("Client Token (for idempotency)", default="")
    if not client_token:
        print_error("Client Token is required")
        return
    
    # Fetch and display available products
    products_url = f"{url}/api/v1/skus"
    try:
        with httpx.Client() as client:
            products_response = client.get(products_url)
            products_response.raise_for_status()
            products = products_response.json()
            
            if not products:
                print_error("No products available. Please create a product first.")
                return
            
            # Display products in a table
            console.print("\n[bold]Available Products:[/bold]")
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("#", style="dim", width=3)
            table.add_column("SKU Code", style="cyan", no_wrap=True)
            table.add_column("Name", style="green")
            table.add_column("Available", justify="right", style="green")
            
            for idx, product in enumerate(products, 1):
                available = product.get('available_qty', 0)
                table.add_row(
                    str(idx),
                    product['sku_code'],
                    product['name'],
                    str(available)
                )
            
            console.print(table)
            
            # Let user select a product
            console.print("\n[dim]Enter product number or SKU ID[/dim]")
            selection = Prompt.ask("Select product", default="")
            
            if not selection:
                print_error("Product selection is required")
                return
            
            # Try to parse as number first
            sku_id = None
            try:
                product_num = int(selection)
                if 1 <= product_num <= len(products):
                    sku_id = products[product_num - 1]['sku_id']
                else:
                    print_error(f"Invalid product number. Please select 1-{len(products)}")
                    return
            except ValueError:
                # Not a number, treat as UUID
                try:
                    UUID(selection)  # Validate UUID format
                    sku_id = selection
                except ValueError:
                    print_error("Invalid selection. Please enter a product number or valid UUID")
                    return
            
            # Show selected product
            selected_product = next((p for p in products if str(p['sku_id']) == str(sku_id)), None)
            if selected_product:
                console.print(f"\n[bold]Selected:[/bold] {selected_product['sku_code']} - {selected_product['name']}")
                console.print(f"[dim]Available: {selected_product.get('available_qty', 0)}[/dim]")
            
    except httpx.HTTPStatusError as e:
        error_detail = get_error_detail(e.response)
        print_error(f"Failed to fetch products: {error_detail}")
        return
    except httpx.RequestError as e:
        print_error(f"Connection Error: Could not connect to {products_url}")
        return
    except Exception as e:
        print_error(f"Error fetching products: {str(e)}")
        return
    
    qty = Prompt.ask("Quantity", default="1")
    try:
        qty = int(qty)
        if qty <= 0:
            print_error("Quantity must be positive")
            return
    except ValueError:
        print_error("Quantity must be a number")
        return
    
    expires_in = Prompt.ask("Expires in (seconds)", default="300")
    try:
        expires_in = int(expires_in)
        if expires_in <= 0:
            print_error("Expiry time must be positive")
            return
    except ValueError:
        print_error("Expiry time must be a number")
        return
    
    strategy = Prompt.ask("Locking Strategy", choices=["optimistic", "pessimistic"], default="optimistic")
    
    data = {
        "client_token": client_token,
        "items": [{"sku_id": sku_id, "qty": qty}],
        "expires_in_seconds": expires_in,
        "strategy": strategy
    }
    
    api_url = f"{url}/api/v1/inventory/holds"
    
    try:
        with httpx.Client() as client:
            response = client.post(api_url, json=data)
            response.raise_for_status()
            reservation = response.json()
            
            print_success(f"Hold created successfully!")
            console.print(f"\n[bold]Reservation Details:[/bold]")
            console.print(f"  Reservation ID: {reservation['reservation_id']}")
            console.print(f"  Status: {reservation['status']}")
            console.print(f"  Expires At: {reservation['expires_at']}")
            
    except httpx.HTTPStatusError as e:
        error_detail = get_error_detail(e.response)
        print_error(f"Failed to create hold: {error_detail}")
    except httpx.RequestError as e:
        print_error(f"Connection Error: Could not connect to {api_url}")
    except Exception as e:
        print_error(f"Error: {str(e)}")


@cli.command()
@click.pass_context
def create_hold(ctx):
    """Create a hold reservation."""
    _create_hold_impl(ctx.obj['url'])


def _consistency_impl(url: str):
    """Check inventory consistency - implementation."""
    api_url = f"{url}/api/v1/inventory/consistency"
    
    try:
        with httpx.Client() as client:
            response = client.get(api_url)
            response.raise_for_status()
            report = response.json()
            
            if report['is_consistent']:
                print_success("Inventory is consistent!")
                console.print(f"\n[bold]Consistency Report:[/bold]")
                console.print(f"  Total SKUs: {report['total_skus']}")
                console.print(f"  Inconsistent SKUs: {len(report['inconsistent_skus'])}")
                console.print(f"  Checked at: {report['timestamp']}")
            else:
                print_error("Inventory consistency issues found!")
                console.print(f"\n[bold]Consistency Report:[/bold]")
                console.print(f"  Total SKUs: {report['total_skus']}")
                console.print(f"  Inconsistent SKUs: {len(report['inconsistent_skus'])}")
                
                if report['inconsistent_skus']:
                    table = Table(title="Inconsistent SKUs", show_header=True, header_style="bold red")
                    table.add_column("SKU ID", style="cyan")
                    table.add_column("Issue", style="red")
                    table.add_column("Details", style="yellow")
                    
                    for item in report['inconsistent_skus']:
                        table.add_row(
                            item['sku_id'],
                            item['issue'],
                            str(item)
                        )
                    console.print(table)
            
    except httpx.HTTPStatusError as e:
        print_error(f"API Error: {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        print_error(f"Connection Error: Could not connect to {api_url}")
    except Exception as e:
        print_error(f"Error: {str(e)}")


@cli.command()
@click.pass_context
def consistency(ctx):
    """Check inventory consistency."""
    _consistency_impl(ctx.obj['url'])


def _health_impl(url: str):
    """Check API health status - implementation."""
    api_url = f"{url}/health"
    
    try:
        with httpx.Client() as client:
            response = client.get(api_url, timeout=5.0)
            response.raise_for_status()
            status = response.json()
            
            if status.get('status') == 'healthy':
                print_success("API is healthy!")
                console.print(f"  Status: {status['status']}")
            else:
                print_error("API health check failed")
                
    except httpx.HTTPStatusError as e:
        print_error(f"API Error: {e.response.status_code}")
    except httpx.RequestError as e:
        print_error(f"Connection Error: Could not connect to {api_url}")
        print_info("Make sure the server is running: uvicorn app.main:app --reload")
    except Exception as e:
        print_error(f"Error: {str(e)}")


@cli.command()
@click.pass_context
def health(ctx):
    """Check API health status."""
    _health_impl(ctx.obj['url'])


def run_interactive(url: str = API_BASE_URL):
    """Run interactive mode (internal function)."""
    console.print(Panel.fit(
        "[bold cyan]Inventory Reservation Service CLI[/bold cyan]\n"
        "Interactive Mode",
        border_style="cyan"
    ))
    
    while True:
        console.print("\n[bold]Available Commands:[/bold]")
        console.print("  1. List Products")
        console.print("  2. Create Product")
        console.print("  3. Check Availability")
        console.print("  4. Create Hold")
        console.print("  5. Check Consistency")
        console.print("  6. Health Check")
        console.print("  7. Exit")
        
        choice = Prompt.ask("\nSelect command", choices=["1", "2", "3", "4", "5", "6", "7"], default="7")
        
        if choice == "1":
            _list_products_impl(url)
        elif choice == "2":
            _create_product_impl(url)
        elif choice == "3":
            _availability_impl(url)
        elif choice == "4":
            _create_hold_impl(url)
        elif choice == "5":
            _consistency_impl(url)
        elif choice == "6":
            _health_impl(url)
        elif choice == "7":
            console.print("\n[green]Goodbye![/green]")
            break


@cli.command()
@click.option('--url', default=API_BASE_URL, help='API base URL')
def interactive(url):
    """Start interactive mode."""
    run_interactive(url)


if __name__ == '__main__':
    cli()