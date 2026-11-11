/* Sample data (DEMO). Django: replace with template context / JSON endpoints. */
window.RC = window.RC || {};
RC.CATEGORIES = [
 {slug:'vintage-electronics',name:'Vintage Electronics',emoji:'📺',hue:215},
 {slug:'antiques',name:'Antiques',emoji:'🕰️',hue:35},
 {slug:'handicrafts',name:'Handicrafts',emoji:'🧸',hue:20},
 {slug:'brass-copper',name:'Brass & Copper',emoji:'🪔',hue:42},
 {slug:'furniture',name:'Wooden Furniture',emoji:'🪑',hue:25},
 {slug:'textiles',name:'Handloom & Textiles',emoji:'🧣',hue:330},
 {slug:'home-decor',name:'Home Decor & Art',emoji:'🖼️',hue:160},
 {slug:'collectibles',name:'Collectibles',emoji:'📷',hue:270}
];
RC.LOCATIONS = ['Thiruvananthapuram, Kerala','Thrissur, Kerala','Kochi, Kerala','Jaipur, Rajasthan','Bastar, Chhattisgarh','Pochampally, Telangana','Channapatna, Karnataka','Madhubani, Bihar'];
/* status: approved | pending | rejected | suspended. sellerDisc/campDisc are percentages. */
RC.PRODUCTS = [
 {id:1,name:'Restored Valve Radio (1960s)',cat:'vintage-electronics',price:4800,sellerDisc:10,campDisc:20,seller:'Restored Radio Works',loc:'Jaipur, Rajasthan',rating:4.7,reviews:212,stock:4,promoted:true,added:'2026-10-20',emoji:'📻',hue:215,status:'approved',desc:'Fully restored tube radio, tested and working on AM/FM with Bluetooth input added discreetly.'},
 {id:2,name:'Old Black & White CRT Television',cat:'vintage-electronics',price:6500,sellerDisc:0,campDisc:15,seller:'Retro Tube Traders',loc:'Kochi, Kerala',rating:4.5,reviews:61,stock:3,promoted:false,added:'2026-10-12',emoji:'📺',hue:200,status:'approved',desc:'Working 14-inch vintage CRT TV in a teak cabinet. Ideal for collectors and film sets.'},
 {id:3,name:'Antique Brass Wall Clock',cat:'antiques',price:3200,sellerDisc:15,campDisc:0,seller:'Thrissur Heritage House',loc:'Thrissur, Kerala',rating:4.6,reviews:88,stock:8,promoted:false,added:'2026-10-22',emoji:'🕰️',hue:35,status:'approved',desc:'Hand-wound pendulum clock with a brass dial, serviced by a master clockmaker.'},
 {id:4,name:'Hand-Carved Rosewood Chair',cat:'furniture',price:7800,sellerDisc:10,campDisc:0,seller:'Kuttanad Woodworks',loc:'Thiruvananthapuram, Kerala',rating:4.8,reviews:174,stock:6,promoted:true,added:'2026-10-21',emoji:'🪑',hue:25,status:'approved',desc:'Solid rosewood armchair with traditional carved back, finished with natural lacquer.'},
 {id:5,name:'Dhokra Brass Horse Figurine',cat:'brass-copper',price:1450,sellerDisc:5,campDisc:0,seller:'Bastar Tribal Artisans',loc:'Bastar, Chhattisgarh',rating:4.9,reviews:301,stock:40,promoted:false,added:'2026-10-24',emoji:'🐴',hue:42,status:'approved',desc:'Lost-wax cast brass figure made by tribal artisans using a 4,000-year-old method.'},
 {id:6,name:'Pochampally Ikat Dupatta',cat:'textiles',price:1200,sellerDisc:10,campDisc:25,seller:'Ikat Weavers Guild',loc:'Pochampally, Telangana',rating:4.5,reviews:49,stock:30,promoted:false,added:'2026-10-05',emoji:'🧣',hue:260,status:'approved',desc:'Handwoven silk-cotton dupatta with traditional double ikat motifs.'},
 {id:7,name:'Aranmula-style Bell Metal Lamp',cat:'brass-copper',price:2200,sellerDisc:0,campDisc:10,seller:'Aranmula Metal Craft',loc:'Thiruvananthapuram, Kerala',rating:4.7,reviews:132,stock:15,promoted:true,added:'2026-10-23',emoji:'🪔',hue:45,status:'approved',desc:'Traditional nilavilakku cast in bell metal, 12 inches tall, with a mirror-bright polish.'},
 {id:8,name:'Vintage Rotary Dial Phone',cat:'vintage-electronics',price:2600,sellerDisc:12,campDisc:0,seller:'Retro Tube Traders',loc:'Kochi, Kerala',rating:4.3,reviews:37,stock:9,promoted:false,added:'2026-10-25',emoji:'📞',hue:190,status:'approved',desc:'Refurbished 1970s rotary phone, converted to work with modern landlines.'},
 {id:9,name:'Channapatna Wooden Toy Set',cat:'handicrafts',price:650,sellerDisc:0,campDisc:15,seller:'Channapatna Toy Makers',loc:'Channapatna, Karnataka',rating:4.6,reviews:96,stock:60,promoted:false,added:'2026-10-18',emoji:'🧸',hue:20,status:'approved',desc:'Lacquered wooden toys coloured with vegetable dyes. Safe for children.'},
 {id:13,name:'Madhubani Painting on Handmade Paper',cat:'home-decor',price:1800,sellerDisc:10,campDisc:0,seller:'Mithila Art Collective',loc:'Madhubani, Bihar',rating:4.6,reviews:54,stock:12,promoted:false,added:'2026-10-19',emoji:'🖼️',hue:160,status:'approved',desc:'Hand-painted fish motif in natural pigments, ready to frame, 16 x 22 inches.'},
 {id:14,name:'Antique Coin Collection (25 pcs)',cat:'collectibles',price:2500,sellerDisc:5,campDisc:0,seller:'Deccan Numismatics',loc:'Thrissur, Kerala',rating:4.4,reviews:29,stock:5,promoted:false,added:'2026-10-14',emoji:'🪙',hue:270,status:'approved',desc:'Authenticated assorted princely-state and colonial-era coins in a wooden case.'},
 {id:10,name:'Vintage Film Camera (Agfa)',cat:'collectibles',price:3900,sellerDisc:0,campDisc:0,seller:'Meena Devi Antiques',loc:'Thiruvananthapuram, Kerala',rating:0,reviews:0,stock:1,promoted:false,added:'2026-10-26',emoji:'📷',hue:270,status:'pending',desc:'Folding bellows camera in working condition.'},
 {id:11,name:'Terracotta Wall Plate',cat:'home-decor',price:350,sellerDisc:10,campDisc:0,seller:'Meena Devi Antiques',loc:'Thiruvananthapuram, Kerala',rating:0,reviews:0,stock:50,promoted:false,added:'2026-10-24',emoji:'🏺',hue:18,status:'rejected',rejectReason:'Photos are unclear. Please upload a well-lit main image.',desc:'Hand-painted terracotta plate.'},
 {id:12,name:'Brass Diya Set (6 pcs)',cat:'brass-copper',price:780,sellerDisc:5,campDisc:0,seller:'Meena Devi Antiques',loc:'Thiruvananthapuram, Kerala',rating:4.5,reviews:54,stock:75,promoted:false,added:'2026-09-30',emoji:'🪔',hue:45,status:'suspended',desc:'Hand-polished brass oil lamps.'}
];
RC.REVIEWS = [
 {name:'Anita R.',rating:5,date:'2026-10-19',text:'Fresh and exactly as described. Packaging was careful.'},
 {name:'Imran S.',rating:4,date:'2026-10-11',text:'Good quality, delivery took a day longer than promised.'},
 {name:'Latha K.',rating:5,date:'2026-09-28',text:'Reminds me of my grandmother\'s kitchen. Will order again.'}
];
RC.MY_SELLER = 'Meena Devi Antiques'; // DEMO identity only. Django: request.user.seller
