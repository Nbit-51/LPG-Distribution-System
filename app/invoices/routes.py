from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List
from app.invoices.schemas import InvoiceResponse, InvoiceListResponse
from app.invoices import service
from app.auth.service import get_current_consumer, get_current_admin

router = APIRouter(prefix="/invoices", tags=["Invoices"])

@router.get("/my", response_model=List[InvoiceResponse])
def get_my_invoices(current_consumer=Depends(get_current_consumer)):
    try:
        return service.get_invoices_by_consumer(current_consumer["consumer_id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/consumer/{consumer_id}", response_model=List[InvoiceResponse])
def get_consumer_invoices(consumer_id: int, _=Depends(get_current_admin)):
    try:
        return service.get_invoices_by_consumer(consumer_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin", response_model=InvoiceListResponse)
def get_all_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _=Depends(get_current_admin)
):
    try:
        return service.get_all_invoices(page, page_size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice_detail(invoice_id: int):
    record = service.get_invoice_by_id(invoice_id)
    if not record:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    return record

@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(invoice_id: int):
    record = service.get_invoice_by_id(invoice_id)
    if not record:
        raise HTTPException(status_code=404, detail="Invoice not found.")
        
    from fastapi.responses import StreamingResponse
    import io
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=40, leftMargin=40,
                            topMargin=40, bottomMargin=40)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#111827'),
        spaceAfter=10
    )
    
    label_style = ParagraphStyle(
        'InvoiceLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#4b5563')
    )
    
    value_style = ParagraphStyle(
        'InvoiceValue',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#1f2937')
    )

    h2_style = ParagraphStyle(
        'InvoiceH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=8,
        spaceBefore=12
    )

    header_data = [
        [
            Paragraph("<b>SMART LPG SYSTEM</b><br/>Priority-Based Distribution Engine", value_style),
            Paragraph("<b>TAX INVOICE</b>", title_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[280, 240])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))
    
    divider = Table([[""]], colWidths=[520], rowHeights=[2])
    divider.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#14b8a6')), # Teal accent color matching frontend
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(divider)
    story.append(Spacer(1, 12))

    issued_str = record["issued_at"].strftime("%d %b %Y, %H:%M") if record.get("issued_at") else "--"
    details_data = [
        [Paragraph("<b>Invoice Number:</b>", label_style), Paragraph(record["invoice_number"], value_style),
         Paragraph("<b>Customer Name:</b>", label_style), Paragraph(record["consumer_name"], value_style)],
        [Paragraph("<b>Issued Date:</b>", label_style), Paragraph(issued_str, value_style),
         Paragraph("<b>LPG Agency:</b>", label_style), Paragraph(record["agency_name"], value_style)],
        [Paragraph("<b>Payment Method:</b>", label_style), Paragraph(record["payment_method"].upper(), value_style),
         Paragraph("<b>Payment Status:</b>", label_style), Paragraph(record["payment_status"].upper(), value_style)],
    ]
    details_table = Table(details_data, colWidths=[100, 160, 100, 160])
    details_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("Invoice Items", h2_style))
    
    amount = float(record["amount"])
    cylinders = int(amount / 850.0) if amount > 0 else 1
    
    from app.database import execute_query
    booking_rows = execute_query(
        "SELECT priority_delivery_fee FROM bookings WHERE booking_id = %s", (record["booking_id"],)
    )
    priority_delivery_fee = 0.00
    if booking_rows and booking_rows[0]["priority_delivery_fee"]:
        priority_delivery_fee = float(booking_rows[0]["priority_delivery_fee"])

    items_data = [
        [
            Paragraph("<b>Description</b>", label_style),
            Paragraph("<b>Quantity</b>", label_style),
            Paragraph("<b>Unit Price</b>", label_style),
            Paragraph("<b>Total (INR)</b>", label_style)
        ],
        [
            Paragraph("LPG Cylinder Refill (14.2 kg)", value_style),
            Paragraph(str(cylinders), value_style),
            Paragraph("Rs. 850.00", value_style),
            Paragraph(f"Rs. {amount:.2f}", value_style)
        ],
        [
            Paragraph("CGST (9%)", value_style),
            Paragraph("-", value_style),
            Paragraph("-", value_style),
            Paragraph(f"Rs. {float(record['cgst']):.2f}", value_style)
        ],
        [
            Paragraph("SGST (9%)", value_style),
            Paragraph("-", value_style),
            Paragraph("-", value_style),
            Paragraph(f"Rs. {float(record['sgst']):.2f}", value_style)
        ],
        [
            Paragraph("Standard Delivery Fee", value_style),
            Paragraph("-", value_style),
            Paragraph("-", value_style),
            Paragraph("Rs. 50.00", value_style)
        ]
    ]
    
    if priority_delivery_fee > 0:
        items_data.append([
            Paragraph("Express Priority Delivery Surcharge", value_style),
            Paragraph("-", value_style),
            Paragraph("-", value_style),
            Paragraph(f"Rs. {priority_delivery_fee:.2f}", value_style)
        ])
        
    items_data.append([
        Paragraph("<b>GRAND TOTAL</b>", label_style),
        Paragraph("", value_style),
        Paragraph("", value_style),
        Paragraph(f"<b>Rs. {float(record['total_amount']):.2f}</b>", label_style)
    ])
    
    items_table = Table(items_data, colWidths=[240, 70, 100, 110])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f3f4f6')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-2), 0.5, colors.HexColor('#e5e7eb')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LINEABOVE', (0,-1), (-1,-1), 1.5, colors.HexColor('#14b8a6')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#f0fdfa')),
    ]))
    
    story.append(items_table)
    story.append(Spacer(1, 20))
    
    footer_text = Paragraph(
        "<center>Thank you for using Smart LPG System.<br/>"
        "This is a computer-generated tax invoice and requires no signature.<br/>"
        "For support, file a ticket in the customer portal.</center>",
        value_style
    )
    story.append(footer_text)
    
    doc.build(story)
    buffer.seek(0)
    
    headers = {
        'Content-Disposition': f'attachment; filename="{record["invoice_number"]}.pdf"'
    }
    return StreamingResponse(buffer, headers=headers, media_type='application/pdf')
